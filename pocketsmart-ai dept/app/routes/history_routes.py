"""
/history (page + JSON API) and lightweight session-introspection
endpoints used for personalization and debugging the current session.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app import database
from app.auth import UserInDB, get_current_active_user
from app.deps import templates

router = APIRouter(tags=["history"])


@router.get("/history", response_class=HTMLResponse)
async def history_page(request: Request, current_user: UserInDB = Depends(get_current_active_user)):
    entries = database.get_history(current_user.username)
    return templates.TemplateResponse(
        request, "history.html", {"user": current_user, "entries": entries}
    )


@router.get("/api/history")
async def history_api(current_user: UserInDB = Depends(get_current_active_user)):
    """Retrieves the user's past recommendation queries and results for review or re-use."""
    return {"username": current_user.username, "history": database.get_history(current_user.username)}


@router.get("/session-info")
async def session_info(current_user: UserInDB = Depends(get_current_active_user)):
    """Retrieves metadata about the current user session, such as user ID and login status."""
    return {
        "username": current_user.username,
        "email": current_user.email,
        "logged_in": True,
        "disabled": current_user.disabled,
    }


@router.get("/session-data")
async def session_data(current_user: UserInDB = Depends(get_current_active_user)):
    """Returns detailed session-specific data used for personalization and recommendation tracking."""
    history = database.get_history(current_user.username)
    categories = {}
    for entry in history:
        categories[entry["category"]] = categories.get(entry["category"], 0) + 1
    return {
        "username": current_user.username,
        "full_name": current_user.full_name,
        "total_recommendations": len(history),
        "recommendations_by_category": categories,
        "last_recommendation": history[0] if history else None,
    }
