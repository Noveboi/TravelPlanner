from typing import Any

from core.models.geography import Coordinates
from core.models.places import Priority, BookingType, Place
from core.tools.foursquare import FoursquarePlace


def convert_fsq_to_place(fsq: FoursquarePlace):
    return Place(
        name=fsq.name,
        coordinates=Coordinates(latitude=fsq.latitude, longitude=fsq.longitude),
        priority=Priority.ESSENTIAL,
        reason_to_go='',
        website=fsq.website,
        booking_type=BookingType.REQUIRED,
        typical_hours_of_stay=0,
        weather_dependent=False
    )

def to_json(obj: Any) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False)

def safe_parse_json_array(text: str) -> list[dict] | None:
    import json, re
    
    # Try the whole text first
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        # Some models return {"report": [...]}
        if isinstance(data, dict) and isinstance(data.get("report"), list):
            return data["report"]
    except Exception:
        pass
    
    # Heuristic: extract the first JSON array in the text
    match = re.search(r"\[\s*{.*}\s*]", text, flags=re.S)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None
    return None