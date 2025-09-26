import logging
import math
from typing import Optional, Any

from langchain_core.tools import BaseTool, ArgsSchema
from pydantic import BaseModel, Field

from core.models.geography import Coordinates


class DistanceToolInput(BaseModel):
    x1: Coordinates = Field(description="The first place's coordinates (latitude, longitude)")
    x2: Coordinates = Field(description="The second place's coordinates (latitude, longitude)")


class DistanceTool(BaseTool):
    name: str = "distance_calculator"
    description: str = "Accurately calculate the distance between two places using their coordinates."
    args_schema: Optional[ArgsSchema] = DistanceToolInput

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._log = logging.getLogger(name='distance_tool')

    def _run(self, x1: Coordinates, x2: Coordinates) -> float:
        """Use the tool"""
        return haversine_distance(x1, x2)


def haversine_distance(x1: Coordinates, x2: Coordinates) -> float:
    """
    Calculates the distance between two places on Earth using the Haversine formula.
    Returns distance in kilometers.
    """
    r = 6371.2  # Earth's radius (km)

    f1, l1 = math.radians(x1.latitude), math.radians(x1.longitude)
    f2, l2 = math.radians(x2.latitude), math.radians(x2.longitude)

    df = f2 - f1
    dl = l2 - l1

    theta = hav(df) + math.cos(f1) * math.cos(f2) * hav(dl)
    return 2 * r * math.asin(math.sqrt(theta))


def hav(theta: float) -> float:
    return (1 - math.cos(theta)) / 2


if __name__ == '__main__':
    paris = Coordinates(latitude=48.8566, longitude=2.3522)
    london = Coordinates(latitude=51.5074, longitude=-0.1278)
    print(haversine_distance(paris, london))  # ~343 km
