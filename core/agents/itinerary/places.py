from core.models.places import Place, Establishment, Event


def estimate_place_cost(place: Place) -> float:
    """
    Estimate the cost for a place.
    :param place: The target
    :return: The estimated price 
    """
    # Assume the cheapest scenario always.
    match place:
        case Establishment(average_price=price):
            return price
        case Event(price_options=options):
            return min(options)
        case _:
            return 0
