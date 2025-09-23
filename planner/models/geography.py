from pydantic import BaseModel, Field

class Coordinates(BaseModel):
    """
    Standard coordinates expressed in latitude and longitude as decimal degrees.
    """
    latitude: float = Field(description='The latitude of the coordinate point.', ge=-90, le=90)
    longitude: float = Field(description='The longitude of the coordinate point.', ge=-180, le=180)
    
    def to_string(self):
        """Return a friendly string representation of the coordinates in the form of {latitude, longitude}"""
        return f'{self.latitude},{self.longitude}'