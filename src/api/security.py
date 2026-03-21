import os
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)

# The Fernet key MUST be exactly 32 url-safe base64-encoded bytes.
# We generate an ephemeral one for local dev fallback so the app does not crash if explicitly unset, 
# although keys encrypted with this fallback will be lost on container restart.
_default_fernet = Fernet.generate_key().decode('utf-8')
FERNET_SECRET_KEY = os.getenv("FERNET_SECRET_KEY", _default_fernet)

try:
    _cipher_suite = Fernet(FERNET_SECRET_KEY.encode('utf-8'))
except Exception as e:
    logger.error("Invalid FERNET_SECRET_KEY provided. Must be a 32-byte base64 string.")
    _cipher_suite = Fernet(_default_fernet.encode('utf-8'))

def encrypt_key(plain_api_key: str) -> str:
    """Encrypts a plaintext API key symmetrically using AES-128 in CBC mode (Fernet)."""
    if not plain_api_key:
        return ""
    return _cipher_suite.encrypt(plain_api_key.encode('utf-8')).decode('utf-8')

def decrypt_key(encrypted_api_key: str) -> str:
    """Decrypts a stored API key using the system FERNET_SECRET_KEY."""
    if not encrypted_api_key:
        return ""
    try:
        return _cipher_suite.decrypt(encrypted_api_key.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error("Failed to decrypt API key. The FERNET_SECRET_KEY may have changed or the string is corrupt.")
        return ""
