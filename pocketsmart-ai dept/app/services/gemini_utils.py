"""
gemini_utils.py
----------------
All Gemini ("Generative AI") orchestration for PocketSmart AI lives
here: prompt construction, budget formatting, domain segmentation,
multimodal (text + image) analysis for the Jewelry planner, JSON
response parsing, and a deterministic fallback path used whenever no
API key is configured or the live call fails, so the product always
returns a usable, well-formed recommendation set.
"""
import json
import logging
import re
import uuid
from typing import List, Optional

from app.config import settings
from app.models.schemas import (
    HomePlannerInput,
    PartyPlannerInput,
    JewelryPlannerInput,
    RecommendedItem,
)
from app.services.product_links import build_search_link, display_platform_name, PLATFORMS_BY_CATEGORY

logger = logging.getLogger("pocketsmart.gemini")

_model = None
_genai = None


def _get_genai_client():
    """Lazily import & configure google-generativeai so the whole app
    still boots even if the package or API key is missing (mock mode)."""
    global _model, _genai
    if settings.is_mock_mode:
        return None
    if _model is not None:
        return _model
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        _genai = genai
        _model = genai.GenerativeModel(settings.GEMINI_MODEL)
        return _model
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Gemini client unavailable, falling back to mock mode: %s", exc)
        return None


# ------------------------------------------------------------------
# Shared helpers
# ------------------------------------------------------------------
def _extract_json_block(text: str):
    """Gemini sometimes wraps JSON in ```json fences or adds prose
    around it. Pull out the first valid JSON array/object it contains."""
    fence_match = re.search(r"```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```", text, re.DOTALL)
    candidate = fence_match.group(1) if fence_match else text

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    array_match = re.search(r"\[.*\]", text, re.DOTALL)
    if array_match:
        try:
            return json.loads(array_match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError("Could not parse a JSON array from the Gemini response")


def _coerce_items(raw_items: list, default_platforms: List[str]) -> List[RecommendedItem]:
    items: List[RecommendedItem] = []
    for i, raw in enumerate(raw_items):
        platform = raw.get("platform") or default_platforms[i % len(default_platforms)]
        query = raw.get("search_query") or raw.get("item_name", "recommendation")
        items.append(
            RecommendedItem(
                category=str(raw.get("category", "General")),
                item_name=str(raw.get("item_name", f"Item {i + 1}")),
                platform=display_platform_name(platform),
                estimated_price=float(raw.get("estimated_price", 0) or 0),
                currency=str(raw.get("currency", "INR")),
                description=str(raw.get("description", "")),
                search_link=build_search_link(platform, query),
            )
        )
    return items


def _finalize_response(planner_type: str, budget: float, items: List[RecommendedItem], source: str) -> dict:
    total_cost = round(sum(item.estimated_price for item in items), 2)
    summary = (
        f"{len(items)} {planner_type} recommendation(s) totaling "
        f"{'within' if total_cost <= budget else 'slightly over'} your "
        f"budget of {budget:,.0f}."
    )
    return {
        "id": str(uuid.uuid4()),
        "planner_type": planner_type,
        "total_budget": budget,
        "total_estimated_cost": total_cost,
        "within_budget": total_cost <= budget,
        "summary": summary,
        "items": [item.model_dump() for item in items],
        "source": source,
    }


def _call_gemini_text(prompt: str, image_parts: Optional[list] = None):
    model = _get_genai_client()
    if model is None:
        return None
    try:
        content = [prompt] if not image_parts else [prompt, *image_parts]
        response = model.generate_content(
            content,
            generation_config={"temperature": 0.4, "response_mime_type": "application/json"},
        )
        return response.text
    except Exception as exc:  # pragma: no cover - defensive, network dependent
        logger.warning("Gemini call failed, using fallback recommendations: %s", exc)
        return None


# ------------------------------------------------------------------
# 1. Home Interior Planner
# ------------------------------------------------------------------
def generate_home_recommendations(data: HomePlannerInput) -> dict:
    rooms_desc = "; ".join(
        f"{r.room_type}: {r.lights} lights, {r.ceiling_fans} ceiling fans, "
        f"{r.dining_tables} dining tables, {r.sofas} sofas, {r.wardrobes} wardrobes"
        + (f" (notes: {r.notes})" if r.notes else "")
        for r in data.rooms
    )
    prompt = f"""You are PocketSmart AI's home-interior budgeting assistant.
A user has a total budget of {data.budget} {data.currency} and wants to
furnish/decorate these rooms: {rooms_desc}.
Style preference: {data.style_preference or "no strong preference"}.
Preferred shopping platforms: {", ".join(data.preferred_platforms)}.

Recommend a cost-effective shopping list that fits the budget as closely
as possible, balancing functionality, style, and price across the listed
platforms. Respond with ONLY a JSON array (no prose, no markdown fences)
where each element has this exact shape:
{{"category": "<room or item category>", "item_name": "<specific product name>",
"platform": "<one of {data.preferred_platforms}>", "estimated_price": <number>,
"currency": "{data.currency}", "description": "<1-2 sentence why this fits>",
"search_query": "<short product search phrase for that platform>"}}
Return between 4 and 10 items in total."""

    text = _call_gemini_text(prompt)
    if text:
        try:
            raw_items = _extract_json_block(text)
            items = _coerce_items(raw_items, data.preferred_platforms or PLATFORMS_BY_CATEGORY["home"])
            return _finalize_response("home", data.budget, items, source="gemini")
        except Exception as exc:
            logger.warning("Failed to parse Gemini home response, using fallback: %s", exc)

    return _fallback_home_recommendations(data)


def _fallback_home_recommendations(data: HomePlannerInput) -> dict:
    platforms = data.preferred_platforms or PLATFORMS_BY_CATEGORY["home"]
    per_room_budget = data.budget / max(len(data.rooms), 1)
    raw_items = []
    catalogue = [
        ("Lighting", "LED Ceiling Light Fixture", 0.12),
        ("Ceiling Fan", "Energy-Efficient Ceiling Fan", 0.15),
        ("Dining", "4-Seater Dining Table Set", 0.30),
        ("Seating", "3-Seater Fabric Sofa", 0.28),
        ("Storage", "2-Door Wardrobe", 0.20),
        ("Decor", "Wall Art & Decorative Accents", 0.08),
    ]
    for room in data.rooms:
        for label, item_name, ratio in catalogue:
            qty = {
                "Lighting": room.lights,
                "Ceiling Fan": room.ceiling_fans,
                "Dining": room.dining_tables,
                "Seating": room.sofas,
                "Storage": room.wardrobes,
            }.get(label, 0)
            if label == "Decor" or qty > 0:
                price = round(per_room_budget * ratio, 2)
                raw_items.append(
                    {
                        "category": f"{room.room_type} - {label}",
                        "item_name": f"{item_name} for {room.room_type}",
                        "platform": platforms[len(raw_items) % len(platforms)],
                        "estimated_price": price,
                        "currency": data.currency,
                        "description": f"Budget-friendly {item_name.lower()} suited for a "
                        f"{data.style_preference or 'versatile'} {room.room_type.lower()}.",
                        "search_query": f"{data.style_preference or ''} {item_name}".strip(),
                    }
                )
    items = _coerce_items(raw_items, platforms)
    return _finalize_response("home", data.budget, items, source="fallback")


# ------------------------------------------------------------------
# 2. Party Planner
# ------------------------------------------------------------------
def generate_party_recommendations(data: PartyPlannerInput) -> dict:
    prompt = f"""You are PocketSmart AI's event-budgeting assistant.
A user is planning a {data.event_type} for {data.guest_count} guests with a
total budget of {data.budget} {data.currency}
{f"in {data.venue_city}" if data.venue_city else ""}.
They {"do" if data.needs_accommodation else "do not"} need accommodation.
Preferred platforms: {", ".join(data.preferred_platforms)}.
Extra notes: {data.notes or "none"}.

Allocate the budget proportionally across catering, decoration,
entertainment, and (if needed) accommodation/venue. Respond with ONLY a
JSON array (no prose, no markdown fences) where each element has this
exact shape:
{{"category": "<Catering|Decoration|Entertainment|Venue|Accommodation>",
"item_name": "<specific package/service name>",
"platform": "<one of {data.preferred_platforms}>", "estimated_price": <number>,
"currency": "{data.currency}", "description": "<1-2 sentence rationale>",
"search_query": "<short search phrase for that platform>"}}
Return between 4 and 8 items in total, tailored to a {data.event_type}."""

    text = _call_gemini_text(prompt)
    if text:
        try:
            raw_items = _extract_json_block(text)
            items = _coerce_items(raw_items, data.preferred_platforms or PLATFORMS_BY_CATEGORY["party"])
            return _finalize_response("party", data.budget, items, source="gemini")
        except Exception as exc:
            logger.warning("Failed to parse Gemini party response, using fallback: %s", exc)

    return _fallback_party_recommendations(data)


def _fallback_party_recommendations(data: PartyPlannerInput) -> dict:
    platforms = data.preferred_platforms or PLATFORMS_BY_CATEGORY["party"]
    allocations = [
        ("Catering", "Swiggy", 0.45, f"Catering package for {data.guest_count} guests"),
        ("Decoration", "Amazon", 0.20, f"{data.event_type} themed decoration set"),
        ("Entertainment", "Zomato", 0.15, f"{data.event_type} entertainment package"),
    ]
    if data.needs_accommodation:
        allocations.append(("Accommodation", "OYO", 0.20, "Guest accommodation booking"))
    else:
        allocations.append(("Venue", "Amazon", 0.20, f"{data.event_type} venue essentials"))

    raw_items = []
    for category, platform, ratio, item_name in allocations:
        raw_items.append(
            {
                "category": category,
                "item_name": item_name,
                "platform": platform,
                "estimated_price": round(data.budget * ratio, 2),
                "currency": data.currency,
                "description": f"{category} option suited to a {data.guest_count}-guest "
                f"{data.event_type.lower()}{f' in {data.venue_city}' if data.venue_city else ''}.",
                "search_query": f"{data.event_type} {category}",
            }
        )
    items = _coerce_items(raw_items, platforms)
    return _finalize_response("party", data.budget, items, source="fallback")


# ------------------------------------------------------------------
# 3. Jewelry Planner (multimodal: text + optional outfit image)
# ------------------------------------------------------------------
def generate_jewelry_recommendations(
    data: JewelryPlannerInput,
    image_bytes: Optional[bytes] = None,
    image_mime: Optional[str] = None,
) -> dict:
    image_note = (
        "An outfit image was provided - factor in its color palette and "
        "style when choosing jewelry that complements it."
        if image_bytes
        else "No outfit image was provided; recommend broadly-flattering options."
    )
    prompt = f"""You are PocketSmart AI's jewelry recommendation assistant.
A user has a budget of {data.budget} {data.currency} for the occasion:
{data.occasion}. Style preference: {data.style_preference or "no strong preference"}.
Metal preference: {data.metal_preference or "no strong preference"}.
Preferred platforms: {", ".join(data.preferred_platforms)}.
{image_note}

Recommend jewelry pieces (e.g. necklace, earrings, bangles, ring) that
match the occasion, style, and (if given) outfit colors, while
respecting the budget. Respond with ONLY a JSON array (no prose, no
markdown fences) where each element has this exact shape:
{{"category": "<Necklace|Earrings|Bangles|Ring|Bracelet|Set>",
"item_name": "<specific product name>",
"platform": "<one of {data.preferred_platforms}>", "estimated_price": <number>,
"currency": "{data.currency}", "description": "<1-2 sentence rationale, mention
color coordination if an outfit image was analyzed>",
"search_query": "<short search phrase for that platform>"}}
Return between 3 and 6 items in total."""

    image_parts = None
    if image_bytes and not settings.is_mock_mode:
        try:
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(image_bytes))
            image_parts = [img]
        except Exception as exc:
            logger.warning("Could not decode outfit image, continuing text-only: %s", exc)

    text = _call_gemini_text(prompt, image_parts=image_parts)
    if text:
        try:
            raw_items = _extract_json_block(text)
            items = _coerce_items(raw_items, data.preferred_platforms or PLATFORMS_BY_CATEGORY["jewelry"])
            return _finalize_response("jewelry", data.budget, items, source="gemini")
        except Exception as exc:
            logger.warning("Failed to parse Gemini jewelry response, using fallback: %s", exc)

    return _fallback_jewelry_recommendations(data, has_image=bool(image_bytes))


def _fallback_jewelry_recommendations(data: JewelryPlannerInput, has_image: bool = False) -> dict:
    platforms = data.preferred_platforms or PLATFORMS_BY_CATEGORY["jewelry"]
    metal = data.metal_preference or "Gold-tone"
    style = data.style_preference or "Classic"
    catalogue = [
        ("Necklace", f"{style} {metal} Necklace", 0.35),
        ("Earrings", f"{style} {metal} Earrings", 0.20),
        ("Bangles", f"{style} {metal} Bangle Set", 0.25),
        ("Ring", f"{style} {metal} Ring", 0.20),
    ]
    color_note = " Colors were matched to your uploaded outfit image." if has_image else ""
    raw_items = []
    for category, item_name, ratio in catalogue:
        raw_items.append(
            {
                "category": category,
                "item_name": item_name,
                "platform": platforms[len(raw_items) % len(platforms)],
                "estimated_price": round(data.budget * ratio, 2),
                "currency": data.currency,
                "description": f"{item_name} suited for {data.occasion}.{color_note}",
                "search_query": item_name,
            }
        )
    items = _coerce_items(raw_items, platforms)
    return _finalize_response("jewelry", data.budget, items, source="fallback")
