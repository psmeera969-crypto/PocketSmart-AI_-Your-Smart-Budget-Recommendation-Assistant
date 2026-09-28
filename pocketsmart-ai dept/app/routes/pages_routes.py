"""
HTML page routes. These render Jinja2 templates for the browser UI;
the actual AI work happens in planner_routes.py via fetch() calls from
the page's JavaScript.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app import database
from app.auth import UserInDB, get_current_active_user, get_optional_user
from app.deps import templates

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = await get_optional_user(request)
    return templates.TemplateResponse(request, "index.html", {"user": user})


@router.get("/testimonials", response_class=HTMLResponse)
async def testimonials(request: Request):
    user = await get_optional_user(request)
    return templates.TemplateResponse(request, "testimonials.html", {"user": user})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    recent = database.get_history(current_user.username)[:5]
    return templates.TemplateResponse(
        request, "dashboard.html", {"user": current_user, "recent": recent}
    )


@router.get("/home-planner", response_class=HTMLResponse)
async def home_planner_page(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    return templates.TemplateResponse(request, "home_planner.html", {"user": current_user})


@router.get("/party-planner", response_class=HTMLResponse)
async def party_planner_page(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    return templates.TemplateResponse(request, "party_planner.html", {"user": current_user})


@router.get("/jewelry-planner", response_class=HTMLResponse)
async def jewelry_planner_page(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    return templates.TemplateResponse(request, "jewelry_planner.html", {"user": current_user})
