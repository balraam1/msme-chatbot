import os
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import bcrypt

security = HTTPBasic()

# Read config from environment variables
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")
ADMIN_JWT_SECRET = os.environ.get("ADMIN_JWT_SECRET", "supersecretjwtkeyforadminpanelauth")
ALGORITHM = "HS256"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies that a plain text password matches a bcrypt hash."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def create_admin_token() -> str:
    """Generates an admin JWT token that expires in 8 hours."""
    expire = datetime.utcnow() + timedelta(hours=8)
    payload = {
        "sub": "admin",
        "role": "admin",
        "exp": expire
    }
    encoded_jwt = jwt.encode(payload, ADMIN_JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def verify_admin_token(token: str) -> bool:
    """Decodes and validates an admin JWT token."""
    try:
        payload = jwt.decode(token, ADMIN_JWT_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username == "admin" and role == "admin":
            return True
        return False
    except JWTError:
        return False

def get_admin_user(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """
    FastAPI dependency that secures admin routes using HTTP Basic Auth.
    Matches username against ADMIN_USERNAME and verifies password against ADMIN_PASSWORD_HASH.
    """
    correct_username = credentials.username == ADMIN_USERNAME
    correct_password = verify_password(credentials.password, ADMIN_PASSWORD_HASH)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect admin username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
