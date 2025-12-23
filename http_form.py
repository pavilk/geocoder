from fastapi import FastAPI, HTTPException
from services.geocoder import fetch_overpass
from models import Address, Coordinates, PlaceOut, CoordinatesWithPlaces
from database.places import get_cached_places, save_places
import httpx
from database.models import init_db
# from typing import Union
from services.geocoder import *

app = FastAPI()


@app.on_event("startup")
async def on_startup():
    await init_db()


@app.post("/address")
async def get_coordinates(addr: Address):
    full_address = f"{addr.city} {addr.street} {addr.house_number}"
    cleaned = clean_address(full_address)

    if isinstance(cleaned, httpx.HTTPStatusError):
        raise HTTPException(
            status_code=cleaned.response.status_code,
            detail=cleaned.args
        )

    final_address = f"Россия {cleaned.get('city')} {cleaned.get('street')} {cleaned.get('house')}"

    cached = await get_cached_address(final_address)
    if cached:
        cached = cached[0]

        places = await get_cached_places(final_address)
        return CoordinatesWithPlaces(
            latitude=cached.latitude,
            longitude=cached.longitude,
            places=[
                PlaceOut(name=p.name, category=p.category)
                for p in places
            ]
        )

    data = await fetch_json(
        "https://nominatim.openstreetmap.org/search",
        {"q": final_address, "format": "json", "limit": 1, "accept-language": "ru"},
    )

    if not data:
        raise HTTPException(status_code=404, detail="Адрес не найден")

    lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
    await save_address(final_address, data[0]["display_name"], lat, lon)

    raw_places = await fetch_overpass(lat, lon)

    places_to_save = []
    places_out = []

    for el in raw_places["elements"]:
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue

        category = (
            tags.get("amenity")
            or tags.get("shop")
            or tags.get("office")
            or "unknown"
        )

        places_out.append(PlaceOut(name=name, category=category))
        places_to_save.append({
            "name": name,
            "category": category,
            "lat": lat,
            "lon": lon,
        })

    await save_places(final_address, places_to_save)

    return CoordinatesWithPlaces(
        latitude=lat,
        longitude=lon,
        places=places_out
    )


@app.post("/coordinates")
async def get_coordinates(coords: Coordinates):
    query = f"{coords.latitude} {coords.longitude}"

    cached = await get_cached_address(query)
    if cached:
        cached = cached[0]
        full_address = cached.full_address
        print(f"[Кеш]\nАдрес: {full_address}")
        return f"[Кеш]\nАдрес: {full_address}"

    try:
        data = await fetch_json(
            "https://nominatim.openstreetmap.org/reverse",
            {"lat": coords.latitude, "lon": coords.longitude, "format": "json", "accept-language": "ru"},
        )
        address = data.get("display_name")
        if not address:
            raise HTTPException(
                status_code=401,
                detail="Адрес не найден."
            )

        print(f"Адрес: {address}")
        await save_address(query, address, coords.latitude, coords.longitude)

        return f"Адрес: {address}"

    except HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.args
        )
