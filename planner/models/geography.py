from dataclasses import dataclass

@dataclass(frozen=True)
class Coordinates:
    """
    Standard coordinates expressed in latitude and longitude as decimal degrees.
    """
    latitude: float
    longitude: float

    def __post_init__(self):
        # Coerce to float and validate ranges
        lat = float(self.latitude)
        lon = float(self.longitude)

        if not (-90.0 <= lat <= 90.0):
            raise ValueError("The latitude of the coordinate point must be between -90 and 90 degrees.")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError("The longitude of the coordinate point must be between -180 and 180 degrees.")

        # Since the dataclass is frozen, use object.__setattr__ to set coerced values
        object.__setattr__(self, "latitude", lat)
        object.__setattr__(self, "longitude", lon)

    def to_string(self) -> str:
        """Return a friendly string representation of the coordinates in the form of {latitude, longitude}"""
        return f"{self.latitude},{self.longitude}"