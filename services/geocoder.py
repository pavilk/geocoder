import aiohttp
import os
from dadata import Dadata
from database.cache import get_cached_address, save_address
from database.places import get_cached_places
from dotenv import load_dotenv
from httpx import HTTPStatusError
import httpx

load_dotenv()

DADATA_TOKEN = os.getenv("DADATA_TOKEN")
DADATA_SECRET = os.getenv("DADATA_SECRET")

dadata = Dadata(DADATA_TOKEN, DADATA_SECRET)


def clean_address(raw_address: str):
    try:
        return dadata.clean("address", raw_address)
    except HTTPStatusError as e:
        print(f"Ошибка Dadata: {e}")
        return e


async def fetch_json(url, params):
    headers = {"User-Agent": "GeoApp/1.0"}
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async with session.get(url, params=params) as resp:
            resp.raise_for_status()
            return await resp.json()


async def fetch_overpass(lat: float, lon: float, radius: int = 200):
    query = f"""
    [out:json];
    (
      node(around:{radius},{lat},{lon})["amenity"];
      node(around:{radius},{lat},{lon})["shop"];
      node(around:{radius},{lat},{lon})["office"];
    );
    out tags;
    """
    url = "https://overpass-api.de/api/interpreter"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=query) as resp:
            resp.raise_for_status()
            return await resp.json()


async def fetch_addresses_by_coords(lat: float, lon: float, limit: int = 5):
    return await fetch_json(
        "https://nominatim.openstreetmap.org/search",
        {
            "q": f"{lat}, {lon}",
            "format": "json",
            "limit": limit,
            "accept-language": "ru",
        },
    )




async def handle_address_input():
    city = input("Город: ").strip()
    street = input("Улица: ").strip()
    house = input("Дом: ").strip()

    if not city or not street or not house:
        print("Пожалуйста, заполните все поля.")
        return

    full_address = f"{city} {street} {house}"

    cleaned = clean_address(full_address)
    if isinstance(cleaned, Exception):
        print("Ошибка нормализации адреса")
        return

    final_address = f"Россия {cleaned.get('city')} {cleaned.get('street')} {cleaned.get('house')}"

    cached = await get_cached_address(final_address)

    if cached:
        print(f"[Кеш]\nШирота: {cached[0].latitude}, Долгота: {cached[0].longitude}")
        places = await get_cached_places(final_address)
        print(places)
        return

    try:
        print(f"Поиск по адресу: {final_address}")
        data = await fetch_json(
            "https://nominatim.openstreetmap.org/search",
            {"q": final_address, "format": "json", "limit": 5, "accept-language": "ru"},
        )

        if not data:
            print("Адрес не найден.")
            return

        answer = data[0]
        lat, lon = float(answer["lat"]), float(answer["lon"])

        print(f"Широта: {lat}, Долгота: {lon}")
        await save_address(final_address, answer["display_name"], lat, lon)

        orgs = await fetch_overpass(lat, lon)

        print("\nОрганизации рядом:")
        if not orgs["elements"]:
            print("Не найдено")
            return

        for el in orgs["elements"]:
            tags = el.get("tags", {})
            name = tags.get("name", "Без названия")
            kind = (
                tags.get("amenity")
                or tags.get("shop")
                or tags.get("office")
                or "unknown"
            )
            print(f"- {name} ({kind})")

    except Exception as e:
        print(f"Ошибка запроса: {e}")


async def handle_coordinates_input():
    coords = input("Введите широту и долготу через пробел: ").strip()
    parts = coords.split()

    if len(parts) != 2:
        print("Нужно ввести два числа: широту и долготу.")
        return

    try:
        lat = float(parts[0])
        lon = float(parts[1])
    except ValueError:
        print("Широта и долгота должны быть числами.")
        return

    print(f"\nПоиск адресов для: {lat}, {lon}")

    try:
        results = await fetch_addresses_by_coords(lat, lon)

        if not results:
            print("Адреса не найдены.")
            return

        print("\nВозможные адреса:")
        for i, item in enumerate(results, 1):
            print(f"{i}. {item.get('display_name')}")

        # сохраняем самый точный
        best = results[0]
        await save_address(
            f"{lat} {lon}",
            best["display_name"],
            lat,
            lon,
        )

    except Exception as e:
        print(f"Ошибка запроса: {e}")


