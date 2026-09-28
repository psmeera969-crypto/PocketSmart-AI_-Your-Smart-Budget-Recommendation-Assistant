"""
Pydantic models (input/output schemas) shared across the app.
"""
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=80)
    password: str = Field(..., min_length=6, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ------------------------------------------------------------------
# Home Interior Planner
# ------------------------------------------------------------------
class RoomItem(BaseModel):
    room_type: str = Field(..., description="e.g. Living Room, Kitchen, Bedroom")
    lights: int = 0
    ceiling_fans: int = 0
    dining_tables: int = 0
    sofas: int = 0
    wardrobes: int = 0
    notes: Optional[str] = None


class HomePlannerInput(BaseModel):
    budget: float = Field(..., gt=0)
    currency: str = "INR"
    style_preference: Optional[str] = Field(None, description="e.g. Modern, Traditional, Minimalist")
    rooms: List[RoomItem]
    preferred_platforms: List[str] = Field(default_factory=lambda: ["Amazon", "IKEA", "Flipkart"])


# ------------------------------------------------------------------
# Party Planner
# ------------------------------------------------------------------
class PartyPlannerInput(BaseModel):
    budget: float = Field(..., gt=0)
    currency: str = "INR"
    guest_count: int = Field(..., gt=0)
    event_type: str = Field(..., description="e.g. Birthday, Wedding, Corporate")
    venue_city: Optional[str] = None
    needs_accommodation: bool = False
    preferred_platforms: List[str] = Field(
        default_factory=lambda: ["Swiggy", "Zomato", "OYO"]
    )
    notes: Optional[str] = None


# ------------------------------------------------------------------
# Jewelry Planner
# ------------------------------------------------------------------
class JewelryPlannerInput(BaseModel):
    budget: float = Field(..., gt=0)
    currency: str = "INR"
    occasion: str = Field(..., description="e.g. Wedding, Engagement, Festival, Party")
    style_preference: Optional[str] = Field(None, description="e.g. Traditional, Modern, Minimal")
    metal_preference: Optional[str] = Field(None, description="e.g. Gold, Silver, Platinum, Diamond")
    preferred_platforms: List[str] = Field(default_factory=lambda: ["Amazon", "Flipkart"])
    # outfit image is handled as an UploadFile at the route level


# ------------------------------------------------------------------
# Recommendation output (shared shape for all three planners)
# ------------------------------------------------------------------
class RecommendedItem(BaseModel):
    category: str
    item_name: str
    platform: str
    estimated_price: float
    currency: str = "INR"
    description: str
    search_link: str


class RecommendationResponse(BaseModel):
    id: str
    planner_type: str
    total_budget: float
    total_estimated_cost: float
    within_budget: bool
    summary: str
    items: List[RecommendedItem]
    source: str = Field(..., description="'gemini' or 'fallback' (mock mode)")
