import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, field_validator
from src.db.neo4j import neo4j_client
from src.api.security import encrypt_key
from src.api.account_policy import (
    normalize_account_email,
    sanitize_full_name,
    validate_password_policy,
)
from src.config.llm_providers import (
    ALLOWED_LLM_PROVIDERS,
    DEFAULT_COMPAT_LLM_MODEL,
    EXAMPLE_COMPATIBLE_BASE_URL,
    EXAMPLE_COMPATIBLE_BASE_URL_DOCKER,
    LLM_PROVIDER_OPENAI,
    LLM_PROVIDER_OPENAI_COMPATIBLE,
    normalize_llm_provider,
    validate_openai_compatible_base_url,
)
from src.config.openai_models import (
    ALLOWED_LLM_MODELS,
    DEFAULT_LLM_MODEL,
    normalize_llm_model_for_provider,
)

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey_change_me_in_prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    tenant_id: str = "default-tenant"

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: Any) -> Any:
        if isinstance(v, str):
            return normalize_account_email(v)
        return v

    @field_validator("full_name", mode="before")
    @classmethod
    def trim_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            return sanitize_full_name(v)
        return v

class Token(BaseModel):
    access_token: str
    token_type: str

class APIKeyUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None


class LLMModelUpdate(BaseModel):
    llm_model: str


class LLMSettingsUpdate(BaseModel):
    llm_provider: str
    llm_model: str
    openai_base_url: Optional[str] = None


class ProfileUpdate(BaseModel):
    full_name: str
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: Any) -> Any:
        if isinstance(v, str):
            return normalize_account_email(v)
        return v

    @field_validator("full_name", mode="before")
    @classmethod
    def trim_name(cls, v: Any) -> Any:
        if isinstance(v, str):
            return sanitize_full_name(v)
        return v


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


# Helpers

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def _user_node_to_dict(user: Any) -> dict:
    return dict(user) if user is not None and not isinstance(user, dict) else (user or {})


def _public_me_payload(user_dict: dict, email_for_lookup: str) -> dict:
    """Strip secrets and graph-only fields; merge LLM settings from dedicated query."""
    settings = neo4j_client.get_user_llm_settings(email_for_lookup) or {}
    provider = normalize_llm_provider(settings.get("llm_provider"))
    payload = {
        "email": user_dict.get("email"),
        "full_name": user_dict.get("full_name"),
        "tenant_id": user_dict.get("tenant_id"),
        "created_at": user_dict.get("created_at"),
        "llm_provider": provider,
        "openai_base_url": (settings.get("openai_base_url") or "") or "",
        "llm_model": normalize_llm_model_for_provider(provider, settings.get("llm_model")),
    }
    return payload

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        raw_sub = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")
        if raw_sub is None or tenant_id is None:
            raise credentials_exception
        email = normalize_account_email(str(raw_sub))
        if not email:
            raise credentials_exception
        return {"email": email, "tenant_id": tenant_id}
    except JWTError:
        raise credentials_exception

# Endpoints
@router.post("/register")
async def register(user: UserRegister):
    try:
        validate_password_policy(user.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not user.full_name:
        raise HTTPException(status_code=400, detail="Full name is required.")
    existing_user = neo4j_client.get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user.password)
    neo4j_client.create_user(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        tenant_id=user.tenant_id.strip() or "default-tenant",
        llm_model=DEFAULT_LLM_MODEL,
    )
    return {"message": "User registered successfully"}

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    login_id = normalize_account_email(form_data.username)
    user = neo4j_client.find_user_for_login(login_id)
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stored_email = user["email"]
    if isinstance(stored_email, str) and normalize_account_email(stored_email) == login_id:
        neo4j_client.safe_canonicalize_stored_email(stored_email, login_id)
        user = neo4j_client.get_user_by_email(login_id) or user

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"], "tenant_id": user["tenant_id"]},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    user = neo4j_client.get_user_by_email(current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    ud = _user_node_to_dict(user)
    return _public_me_payload(ud, current_user["email"])


@router.put("/profile")
async def update_profile(body: ProfileUpdate, current_user: dict = Depends(get_current_user)):
    if not body.full_name:
        raise HTTPException(status_code=400, detail="Full name cannot be empty.")
    neo4j_client.update_user_full_name(current_user["email"], body.full_name)
    new_email = normalize_account_email(str(body.email))
    token_out: Optional[str] = None
    if new_email != current_user["email"]:
        if neo4j_client.count_users_by_email(new_email) > 0:
            raise HTTPException(status_code=400, detail="That email is already registered.")
        neo4j_client.update_user_login_email(current_user["email"], new_email)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token_out = create_access_token(
            data={"sub": new_email, "tenant_id": current_user["tenant_id"]},
            expires_delta=access_token_expires,
        )
    user = neo4j_client.get_user_by_email(new_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    payload = _public_me_payload(_user_node_to_dict(user), new_email)
    out: dict = {"message": "Profile updated.", "user": payload}
    if token_out:
        out["access_token"] = token_out
        out["token_type"] = "bearer"
    return out


@router.put("/password")
async def change_password(body: PasswordChange, current_user: dict = Depends(get_current_user)):
    try:
        validate_password_policy(body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    user = neo4j_client.get_user_by_email(current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(body.current_password, user["password"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")
    neo4j_client.update_user_password_hash(current_user["email"], get_password_hash(body.new_password))
    return {"message": "Password updated."}


@router.get("/llm-models")
async def list_llm_models():
    """Public allowlist for profile UI."""
    return {"models": ALLOWED_LLM_MODELS, "default": DEFAULT_LLM_MODEL}


@router.get("/llm-config")
async def llm_config():
    """Profile UI: providers, cloud model list, defaults."""
    return {
        "providers": [
            {"id": LLM_PROVIDER_OPENAI, "label": "OpenAI (cloud)"},
            {"id": LLM_PROVIDER_OPENAI_COMPATIBLE, "label": "OpenAI-compatible (Ollama, LM Studio, …)"},
        ],
        "openai_models": ALLOWED_LLM_MODELS,
        "default_openai_model": DEFAULT_LLM_MODEL,
        "default_compatible_model": DEFAULT_COMPAT_LLM_MODEL,
        "example_compatible_base_url": EXAMPLE_COMPATIBLE_BASE_URL,
        "example_compatible_base_url_docker": EXAMPLE_COMPATIBLE_BASE_URL_DOCKER,
        "compatible_base_url_hint": (
            "Use …/v1 (chat API). http://host:11434/ is only Ollama’s status page. "
            "If the API runs in Docker, use host.docker.internal instead of localhost."
        ),
    }


@router.put("/llm-model")
async def update_llm_model(
    body: LLMModelUpdate,
    current_user: dict = Depends(get_current_user),
):
    settings = neo4j_client.get_user_llm_settings(current_user["email"])
    if not settings:
        raise HTTPException(status_code=404, detail="User not found")
    provider = normalize_llm_provider(settings.get("llm_provider"))
    cleaned = body.llm_model.strip()
    if provider == LLM_PROVIDER_OPENAI_COMPATIBLE:
        if not cleaned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="llm_model must be a non-empty model id for OpenAI-compatible backends.",
            )
        if len(cleaned) > 200:
            cleaned = cleaned[:200]
    else:
        if cleaned not in ALLOWED_LLM_MODELS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid llm_model. Allowed: {ALLOWED_LLM_MODELS}",
            )
    neo4j_client.set_user_llm_model(current_user["email"], cleaned)
    return {"message": "LLM model preference saved.", "llm_model": cleaned}


@router.put("/llm-settings")
async def update_llm_settings(
    body: LLMSettingsUpdate,
    current_user: dict = Depends(get_current_user),
):
    if not neo4j_client.get_user_by_email(current_user["email"]):
        raise HTTPException(status_code=404, detail="User not found")
    provider = normalize_llm_provider(body.llm_provider)
    if provider not in ALLOWED_LLM_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid llm_provider. Allowed: {list(ALLOWED_LLM_PROVIDERS)}",
        )
    base_stored: Optional[str] = None
    if provider == LLM_PROVIDER_OPENAI_COMPATIBLE:
        try:
            base_stored = validate_openai_compatible_base_url(body.openai_base_url or "")
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    model_in = body.llm_model.strip()
    if provider == LLM_PROVIDER_OPENAI:
        if model_in not in ALLOWED_LLM_MODELS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid llm_model for OpenAI. Allowed: {ALLOWED_LLM_MODELS}",
            )
        llm_model = model_in
    else:
        if not model_in:
            llm_model = DEFAULT_COMPAT_LLM_MODEL
        else:
            llm_model = model_in[:200] if len(model_in) > 200 else model_in
    neo4j_client.set_user_llm_settings(
        current_user["email"],
        llm_provider=provider,
        llm_model=llm_model,
        openai_base_url=base_stored,
    )
    return {
        "message": "LLM settings saved.",
        "llm_provider": provider,
        "llm_model": llm_model,
        "openai_base_url": base_stored or "",
    }

@router.put("/api-keys")
async def update_api_keys(keys: APIKeyUpdate, current_user: dict = Depends(get_current_user)):
    enc_openai = encrypt_key(keys.openai_api_key) if keys.openai_api_key else None
    enc_tavily = encrypt_key(keys.tavily_api_key) if keys.tavily_api_key else None
    
    neo4j_client.update_user_api_keys(current_user["email"], enc_openai, enc_tavily)
    return {"message": "API Keys saved securely."}

@router.get("/api-keys/status")
async def get_api_key_status(current_user: dict = Depends(get_current_user)):
    keys = neo4j_client.get_user_api_keys(current_user["email"])
    settings = neo4j_client.get_user_llm_settings(current_user["email"]) or {}
    provider = normalize_llm_provider(settings.get("llm_provider"))
    return {
        "has_openai_key": bool(keys.get("openai")),
        "has_tavily_key": bool(keys.get("tavily")),
        "llm_provider": provider,
        "requires_openai_api_key": provider == LLM_PROVIDER_OPENAI,
    }
