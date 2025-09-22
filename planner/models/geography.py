from pydantic import BaseModel, Field

class Coordinates(BaseModel):
    latitude: float = Field(description='The latitude of the coordinate point.', ge=-90, le=90)
    longitude: float = Field(description='The longitude of the coordinate point.', ge=-180, le=180)
    
    def to_string(self):
        return f'{self.latitude},{self.longitude}'