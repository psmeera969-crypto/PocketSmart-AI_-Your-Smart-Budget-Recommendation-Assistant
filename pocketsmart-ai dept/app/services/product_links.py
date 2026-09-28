"""
Deterministic "platform linking" helper.

Gemini is good at suggesting *what* to buy/book (item names, categories,
price ranges) but it cannot reliably know a specific, currently-valid
product URL. Rather than let the model hallucinate a fake product page,
PocketSmart AI builds a real, working *search-results* URL on the
target platform for the suggested item - the user lands on genuine
live results they can browse and buy from.
"""
from urllib.parse import quote_plus

_SEARCH_URL_TEMPLATES = {
    "amazon": "https://www.amazon.in/s?k={q}",
    "flipkart": "https://www.flipkart.com/search?q={q}",
    "ikea": "https://www.ikea.com/in/en/search/?q={q}",
    "swiggy": "https://www.swiggy.com/search?query={q}",
    "zomato": "https://www.zomato.com/search?q={q}",
    "oyo": "https://www.oyorooms.com/search?searchString={q}",
}

# Which platforms are relevant for which planner, used as a sensible
# default / fallback rotation when Gemini doesn't name a platform.
PLATFORMS_BY_CATEGORY = {
    "home": ["Amazon", "IKEA", "Flipkart"],
    "party": ["Swiggy", "Zomato", "OYO"],
    "jewelry": ["Amazon", "Flipkart"],
}


def normalize_platform(name: str) -> str:
    """Map a free-text platform name to one of our known keys, defaulting
    to Amazon (the most universal marketplace) if we don't recognize it."""
    key = (name or "").strip().lower()
    for known in _SEARCH_URL_TEMPLATES:
        if known in key:
            return known
    return "amazon"


def build_search_link(platform: str, query: str) -> str:
    key = normalize_platform(platform)
    template = _SEARCH_URL_TEMPLATES[key]
    return template.format(q=quote_plus(query.strip()))


def display_platform_name(platform: str) -> str:
    key = normalize_platform(platform)
    return {
        "amazon": "Amazon",
        "flipkart": "Flipkart",
        "ikea": "IKEA",
        "swiggy": "Swiggy",
        "zomato": "Zomato",
        "oyo": "OYO",
    }[key]
