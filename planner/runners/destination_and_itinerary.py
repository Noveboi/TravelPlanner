import datetime

from planner.agents.itinerary.itinerary_agent import ItineraryBuilderAgent
from planner.agents.places.destination_scout import DestinationScoutAgent
from planner.runners.setup import log, llm, example_request
from planner.tools.foursquare import FoursquareApiClient


def _safe_filename_component(text: str) -> str:
    """
    Sanitize a string to be safe for file names across operating systems.
    Keeps alphanumerics, dashes, and underscores; replaces others with underscores.
    """
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in text.strip().lower())


if __name__ == '__main__':
    scout_agent = DestinationScoutAgent(
        llm=llm,
        client=FoursquareApiClient()
    )

    report = scout_agent.invoke(example_request)
    log.info('Finished scouting')
    itinerary_agent = ItineraryBuilderAgent(llm)

    itinerary = itinerary_agent.invoke(example_request, report)

    # Build a Windows-safe filename by sanitizing destination and timestamp
    dest_part = _safe_filename_component(example_request.destination)
    timestamp_part = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_name = f'{dest_part}_itinerary_{timestamp_part}.json'

    with open(file_name, 'w', encoding='utf-8') as f:
        f.write(itinerary.model_dump_json(indent=4))

    print('Done!')
