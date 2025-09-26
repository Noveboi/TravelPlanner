from typing import Any


def to_json(obj: Any) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False)
