from pydantic import BaseModel
from typing import List


class PlaceOut(BaseModel):
    name: str
    category: str


class CoordinatesWithPlaces(BaseModel):
    latitude: float
    longitude: float
    places: List[PlaceOut]

class Address(BaseModel):
    city: str
    street: str
    house_number: int

class Coordinates(BaseModel):
    latitude: float
    longitude: float

