import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from src.db.neo4j import neo4j_client
from src.api.security import encrypt_key
from src.config.openai_models import (
    ALLOWED_LLM_MODELS,
    DEFAULT_LLM_MODEL,
    normalize_llm_model,
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

class Token(BaseModel):
    access_token: str
    token_type: str

class APIKeyUpdate(BaseModel):
    openai_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None


class LLMModelUpdate(BaseModel):
    llm_model: str

# Helpers

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

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
        email: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")
        if email is None or tenant_id is None:
            raise credentials_exception
        return {"email": email, "tenant_id": tenant_id}
    except JWTError:
        raise credentials_exception

# Endpoints
@router.post("/register")
async def register(user: UserRegister):
    existing_user = neo4j_client.get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    neo4j_client.create_user(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        tenant_id=user.tenant_id,
        llm_model=DEFAULT_LLM_MODEL,
    )
    return {"message": "User registered successfully"}

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = neo4j_client.get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user['password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user['email'], "tenant_id": user['tenant_id']},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    user = neo4j_client.get_user_by_email(current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Don't return the password
    user_data: dict = dict(user)
    user_data.pop('password', None)
    raw_model = neo4j_client.get_user_llm_model(current_user["email"])
    user_data["llm_model"] = normalize_llm_model(raw_model)
    return user_data


@router.get("/llm-models")
async def list_llm_models():
    """Public allowlist for profile UI."""
    return {"models": ALLOWED_LLM_MODELS, "default": DEFAULT_LLM_MODEL}


@router.put("/llm-model")
async def update_llm_model(
    body: LLMModelUpdate,
    current_user: dict = Depends(get_current_user),
):
    cleaned = body.llm_model.strip()
    if cleaned not in ALLOWED_LLM_MODELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid llm_model. Allowed: {ALLOWED_LLM_MODELS}",
        )
    neo4j_client.set_user_llm_model(current_user["email"], cleaned)
    return {"message": "LLM model preference saved.", "llm_model": cleaned}

@router.put("/api-keys")
async def update_api_keys(keys: APIKeyUpdate, current_user: dict = Depends(get_current_user)):
    enc_openai = encrypt_key(keys.openai_api_key) if keys.openai_api_key else None
    enc_tavily = encrypt_key(keys.tavily_api_key) if keys.tavily_api_key else None
    
    neo4j_client.update_user_api_keys(current_user["email"], enc_openai, enc_tavily)
    return {"message": "API Keys saved securely."}

@router.get("/api-keys/status")
async def get_api_key_status(current_user: dict = Depends(get_current_user)):
    keys = neo4j_client.get_user_api_keys(current_user["email"])
    return {
        "has_openai_key": bool(keys.get("openai")),
        "has_tavily_key": bool(keys.get("tavily"))
    }
