from pydantic import BaseModel, Field, model_validator


class Latitude(BaseModel):
    value: int = Field(..., ge=-90, le=90, description="Degrees (-90 to 90)")
    minutes: int = Field(..., ge=0, lt=60, description="Minutes (0–59)")
    seconds: int = Field(..., ge=0, lt=60, description="Seconds (0–59)")

    @model_validator(mode="after")
    def check_poles(self):
        if abs(self.value) == 90 and (self.minutes > 0 or self.seconds > 0):
            raise ValueError("Latitude cannot exceed ±90°00′00″")
        return self


class Longitude(BaseModel):
    value: int = Field(..., ge=-180, le=180, description="Degrees (-180 to 180)")
    minutes: int = Field(..., ge=0, lt=60, description="Minutes (0–59)")
    seconds: int = Field(..., ge=0, lt=60, description="Seconds (0–59)")

    @model_validator(mode="after")
    def check_bounds(self):
        if abs(self.value) == 180 and (self.minutes > 0 or self.seconds > 0):
            raise ValueError("Longitude cannot exceed ±180°00′00″")
        return self


class Coordinates(BaseModel):
    latitude: Latitude
    longitude: Longitude
