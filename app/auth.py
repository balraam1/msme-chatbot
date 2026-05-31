import os
import base64
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status, Request
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

async def get_admin_user(request: Request) -> str:
    """
    FastAPI dependency that secures admin routes.
    Supports either HTTP Basic Auth (username/password) or Bearer Token (JWT).
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Header",
            headers={"WWW-Authenticate": "Basic, Bearer"},
        )
        
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):].strip()
        if verify_admin_token(token):
            return "admin"
            
    elif auth_header.startswith("Basic "):
        try:
            encoded = auth_header[len("Basic "):].strip()
            decoded = base64.b64decode(encoded).decode("utf-8")
            username, password = decoded.split(":", 1)
            correct_username = username == ADMIN_USERNAME
            correct_password = verify_password(password, ADMIN_PASSWORD_HASH)
            if correct_username and correct_password:
                return username
        except Exception:
            pass
            
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials or token",
        headers={"WWW-Authenticate": "Basic, Bearer"},
    )

