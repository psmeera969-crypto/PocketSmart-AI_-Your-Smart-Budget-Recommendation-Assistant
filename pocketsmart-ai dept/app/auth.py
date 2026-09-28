"""
Authentication & session handling for PocketSmart AI.

- Passwords are hashed with bcrypt (passlib).
- Sessions are backed by short-lived JWTs.
- The JWT is delivered two ways so both the browser UI and API
  clients (curl / Swagger "Authorize") can use it:
    1. An httpOnly cookie named "access_token" (used by the HTML pages).
    2. A standard "Authorization: Bearer <token>" header (used by /docs
       and programmatic API calls), issued via the OAuth2 /token route.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.config import settings
from app import database

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# tokenUrl only matters for the interactive /docs "Authorize" button.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


class TokenData(BaseModel):
    username: Optional[str] = None


class UserInDB(BaseModel):
    username: str
    email: str
    full_name: str
    disabled: bool = False


# ------------------------------------------------------------------
# Password helpers
# ------------------------------------------------------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# ------------------------------------------------------------------
# User helpers
# ------------------------------------------------------------------
def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    record = database.get_user(username)
    if not record:
        return None
    if not verify_password(password, record["hashed_password"]):
        return None
    return UserInDB(**{k: record[k] for k in ("username", "email", "full_name", "disabled")})


# ------------------------------------------------------------------
# JWT helpers
# ------------------------------------------------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return TokenData(username=username)
    except JWTError:
        return None


def _extract_token(request: Request, header_token: Optional[str]) -> Optional[str]:
    """Prefer the cookie (browser session); fall back to the Bearer header (API clients)."""
    cookie_token = request.cookies.get("access_token") if request else None
    if cookie_token:
        return cookie_token
    return header_token


async def get_current_user(
    request: Request, token: Optional[str] = Depends(oauth2_scheme)
) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    raw_token = _extract_token(request, token)
    if not raw_token:
        raise credentials_exception

    token_data = decode_token(raw_token)
    if token_data is None or token_data.username is None:
        raise credentials_exception

    record = database.get_user(token_data.username)
    if record is None:
        raise credentials_exception

    return UserInDB(**{k: record[k] for k in ("username", "email", "full_name", "disabled")})


async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_optional_user(request: Request) -> Optional[UserInDB]:
    """Non-raising variant used by public pages that render differently
    for logged-in vs anonymous visitors (e.g. the landing page nav bar)."""
    raw_token = request.cookies.get("access_token")
    if not raw_token:
        return None
    token_data = decode_token(raw_token)
    if not token_data or not token_data.username:
        return None
    record = database.get_user(token_data.username)
    if not record:
        return None
    return UserInDB(**{k: record[k] for k in ("username", "email", "full_name", "disabled")})
