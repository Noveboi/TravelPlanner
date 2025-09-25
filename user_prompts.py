from datetime import datetime
from typing import Any, Callable

from core.models.trip import TripRequest, TripType


def should_use_preset_request() -> bool:
    response = input('Would you like to use a preset trip request? (y/N)')
    
    if 'y' in response.lower():
        return True
    
    return False

def create_trip_request() -> TripRequest:
    prompts: list[tuple[str, str, Callable[[str], Any]]] = [
        ('Where do you want to go? ✈️', 'destination', lambda x: x),
        ('When do you arrive? 📅 (dd-MM-yyyy)', 'start_date', lambda x: datetime.strptime(x, "%d-%m-%Y")),
        ('When do you depart? 📅 (dd-MM-yyyy)', 'end_date', lambda x: datetime.strptime(x, "%d-%m-%Y")),
        ('What is your budget? 💵 (Euros)', 'budget', lambda x: float(x)),
        ('How many people? 🙋', 'travelers', lambda x: int(x)),
        ('What type of trip is this? (Solo, Couple, Friends or Group)', 'trip_type', lambda x: TripType[x])
    ]
    
    request: dict[str, Any] = {}
    total_questions = len(prompts)
    
    for num, (prompt, field, convert) in enumerate(prompts, start=1):
        response: str = input(f"[{num}/{total_questions}] {prompt}")
        
        while True:
            try:
                request[field] = convert(response)
                break
            except Exception:
                response = input('The input was not correct, try again!')
    
    return TripRequest.model_validate(request)
    
def should_pretty_print_to_console() -> bool:
    response = input('Would you like to pretty print the itinerary to the console? (Y/n)')
    
    if 'n' in response.lower():
        return False
    
    return True