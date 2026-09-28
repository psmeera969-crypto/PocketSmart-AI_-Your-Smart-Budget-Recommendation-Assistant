"""
The three core recommendation endpoints plus a detail-lookup route.
Each /generate-* endpoint: validates input -> calls gemini_utils ->
stores the result in the user's history -> returns JSON the frontend
JS renders into result cards.
"""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from app import database
from app.auth import UserInDB, get_current_active_user
from app.models.schemas import (
    HomePlannerInput,
    JewelryPlannerInput,
    PartyPlannerInput,
    RecommendationResponse,
    RoomItem,
)
from app.services import gemini_utils

router = APIRouter(tags=["planners"])

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


# ------------------------------------------------------------------
# Home Interior Planner
# ------------------------------------------------------------------
@router.post("/generate-home", response_model=RecommendationResponse)
async def generate_home(
    payload: HomePlannerInput, current_user: UserInDB = Depends(get_current_active_user)
):
    if not payload.rooms:
        raise HTTPException(status_code=422, detail="Please add at least one room.")

    result = gemini_utils.generate_home_recommendations(payload)
    database.add_history_entry(current_user.username, "home", payload.model_dump(), result)
    return result


# ------------------------------------------------------------------
# Party Planner
# ------------------------------------------------------------------
@router.post("/generate-party", response_model=RecommendationResponse)
async def generate_party(
    payload: PartyPlannerInput, current_user: UserInDB = Depends(get_current_active_user)
):
    result = gemini_utils.generate_party_recommendations(payload)
    database.add_history_entry(current_user.username, "party", payload.model_dump(), result)
    return result


# ------------------------------------------------------------------
# Jewelry Planner (multipart form: fields + optional outfit image)
# ------------------------------------------------------------------
@router.post("/generate-jewelry", response_model=RecommendationResponse)
async def generate_jewelry(
    budget: float = Form(...),
    currency: str = Form("INR"),
    occasion: str = Form(...),
    style_preference: Optional[str] = Form(None),
    metal_preference: Optional[str] = Form(None),
    preferred_platforms: str = Form("Amazon,Flipkart"),
    outfit_image: Optional[UploadFile] = File(None),
    current_user: UserInDB = Depends(get_current_active_user),
):
    try:
        payload = JewelryPlannerInput(
            budget=budget,
            currency=currency,
            occasion=occasion,
            style_preference=style_preference,
            metal_preference=metal_preference,
            preferred_platforms=[p.strip() for p in preferred_platforms.split(",") if p.strip()],
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=json.loads(exc.json()))

    image_bytes: Optional[bytes] = None
    image_mime: Optional[str] = None
    if outfit_image is not None and outfit_image.filename:
        image_bytes = await outfit_image.read()
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="Outfit image must be under 5 MB.")
        image_mime = outfit_image.content_type

    result = gemini_utils.generate_jewelry_recommendations(payload, image_bytes, image_mime)

    input_record = payload.model_dump()
    input_record["outfit_image_provided"] = bool(image_bytes)
    database.add_history_entry(current_user.username, "jewelry", input_record, result)
    return result


# ------------------------------------------------------------------
# Recommendation detail lookup (used by history "view again")
# ------------------------------------------------------------------
@router.get("/recommendations-details/{entry_id}")
async def recommendation_details(entry_id: str, current_user: UserInDB = Depends(get_current_active_user)):
    entry = database.get_history_entry(current_user.username, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Recommendation not found.")
    return entry
