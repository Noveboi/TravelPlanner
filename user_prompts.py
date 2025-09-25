from datetime import datetime
from typing import Any, Callable, Iterable

from core.models.trip import TripRequest, TripType


def should_use_preset_request() -> bool:
    response = input('Would you like to use a preset trip request? (y/N)\n')
    return 'y' in response.lower()


def _prompt_until_valid(prompt: str, convert: Callable[[str], Any],
                        error_msg: str = 'The input was not correct, try again!') -> Any:
    while True:
        response = input(prompt + '\n')
        try:
            return convert(response)
        except Exception:
            print(error_msg)
            continue


def _parse_date(s: str) -> datetime:
    # Accept common variants
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError("Invalid date format. Try dd-MM-yyyy (e.g., 25-12-2026).")


def _parse_float(s: str) -> float:
    return float(s.replace(',', '.').strip())


def _parse_int(s: str) -> int:
    return int(s.strip())


def _parse_trip_type(s: str) -> TripType:
    aliases: dict[str, TripType] = {
        "SOLO": TripType.SOLO,
        "COUPLE": TripType.COUPLE,
        "FRIENDS": TripType.FRIENDS,
        "GROUP": TripType.GROUP,
    }
    key = s.strip().upper()
    if key in aliases:
        return aliases[key]
    raise ValueError("Valid options: Solo, Couple, Friends, Group.")


def _collect_list(prompt_iter: Iterable[str], min_items: int = 1) -> list[str]:
    items: list[str] = []
    for label in prompt_iter:
        value = input(label)
        if value.strip() == "-q":
            if len(items) >= min_items:
                break
            print(f'You must enter at least {min_items} item(s)!')
            continue
        if value.strip():
            items.append(value.strip())
    return items


def create_trip_request() -> TripRequest:
    prompts: list[tuple[str, str, Callable[[str], Any]]] = [
        ('Where do you want to go? ✈️', 'destination', lambda x: x.strip()),
        ('When do you arrive? 📅 (dd-MM-yyyy)', 'start_date', _parse_date),
        ('When do you depart? 📅 (dd-MM-yyyy)', 'end_date', _parse_date),
        ('What is your budget? 💵 (Euros)', 'budget', _parse_float),
        ('How many people? 🙋', 'travelers', _parse_int),
        ('What type of trip is this? (Solo, Couple, Friends or Group)', 'trip_type', _parse_trip_type),
    ]

    request: dict[str, Any] = {}
    total_questions = len(prompts) + 1  # interests asked separately

    for num, (prompt, field, convert) in enumerate(prompts, start=1):
        value = _prompt_until_valid(f"[{num}/{total_questions}] {prompt}", convert)
        request[field] = value

    # Validate date order
    if request['end_date'] <= request['start_date']:
        print("Departure must be after arrival. Let's re-enter the dates.")
        request['start_date'] = _prompt_until_valid(
            f"[{len(prompts)}/{total_questions}] When do you arrive? 📅 (dd-MM-yyyy)",
            _parse_date
        )
        request['end_date'] = _prompt_until_valid(
            f"[{len(prompts)}/{total_questions}] When do you depart? 📅 (dd-MM-yyyy)",
            _parse_date
        )

    print(f'[{total_questions}/{total_questions}] '
          f'Enter your interests for this trip, what would you like to see/do? '
          f'(Enter "-q" to finish)')
    interests = _collect_list((f'Interest #{i}: ' for i in range(1, 1000)), min_items=1)
    request['interests'] = interests

    return TripRequest.model_validate(request)


def should_pretty_print_to_console() -> bool:
    response = input('Would you like to pretty print the itinerary to the console? (Y/n)\n')
    return 'n' not in response.lower()
