"""
/register, /login, /logout, /token
------------------------------------
Handles new user registration, credential authentication, session
(cookie) issuance/termination, and a standard OAuth2 password-flow
/token endpoint so the API can also be driven from curl, Postman, or
the interactive /docs "Authorize" button.
"""
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm

from app import database
from app.auth import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_optional_user,
)
from app.config import settings
from app.deps import templates
from app.models.schemas import Token

router = APIRouter(tags=["auth"])

COOKIE_NAME = "access_token"
COOKIE_MAX_AGE = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


# ------------------------------------------------------------------
# Register
# ------------------------------------------------------------------
@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    user = await get_optional_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request, "register.html", {"error": None})


@router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    if password != confirm_password:
        return templates.TemplateResponse(
            request, "register.html", {"error": "Passwords do not match."}, status_code=400
        )
    if database.get_user(username):
        return templates.TemplateResponse(
            request, "register.html", {"error": "That username is already taken."}, status_code=400
        )
    if database.get_user_by_email(email):
        return templates.TemplateResponse(
            request, "register.html", {"error": "An account with that email already exists."},
            status_code=400,
        )

    database.create_user(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=get_password_hash(password),
    )

    token = create_access_token({"sub": username.lower()})
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(COOKIE_NAME, token, httponly=True, max_age=COOKIE_MAX_AGE, samesite="lax")
    return response


# ------------------------------------------------------------------
# Login
# ------------------------------------------------------------------
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = await get_optional_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    user = authenticate_user(username, password)
    if not user:
        return templates.TemplateResponse(
            request, "login.html", {"error": "Incorrect username or password."}, status_code=401
        )
    token = create_access_token({"sub": user.username.lower()})
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(COOKIE_NAME, token, httponly=True, max_age=COOKIE_MAX_AGE, samesite="lax")
    return response


# ------------------------------------------------------------------
# Logout
# ------------------------------------------------------------------
@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(COOKIE_NAME)
    return response


# ------------------------------------------------------------------
# OAuth2 token endpoint (for API clients / Swagger "Authorize")
# ------------------------------------------------------------------
@router.post("/token", response_model=Token)
async def issue_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user.username.lower()})
    return Token(access_token=token, token_type="bearer")
