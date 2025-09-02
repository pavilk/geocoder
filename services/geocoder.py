import aiohttp
from dadata import Dadata
from database.cache import get_cached_address, save_address

DADATA_TOKEN = "52a1b45a5b5ff4923bac96cc0f0453ace082e9ab"
DADATA_SECRET = "669e20c2239bc14137989e5d4375582dc68d9e98"
dadata = Dadata(DADATA_TOKEN, DADATA_SECRET)


def clean_address(raw_address: str):
    try:
        return dadata.clean("address", raw_address)
    except Exception as e:
        print(f"Ошибка Dadata: {e}")
        return None


async def fetch_json(url, params):
    headers = {"User-Agent": "GeoApp/1.0"}
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async with session.get(url, params=params) as resp:
            resp.raise_for_status()
            return await resp.json()


async def handle_address_input():
    city = input("Город: ").strip()
    street = input("Улица: ").strip()
    house = input("Дом: ").strip()

    if not city or not street or not house:
        print("Пожалуйста, заполните все поля.")
        return

    full_address = f"{city} {street} {house}"

    cleaned = clean_address(full_address)
    if not cleaned:
        print("Ошибка нормализации адреса.")
        return

    finall_addres = f"Россия {cleaned.get('city')} {cleaned.get('street')} {cleaned.get('house')}"
    if not finall_addres:
        print("Ошибка нормализации адреса.")
        return

    cached = await get_cached_address(finall_addres)
    if cached:
        print(f"[Кеш]\nШирота: {cached.latitude}, Долгота: {cached.longitude}")
        return

    try:
        print(f"Поиск по адресу: {finall_addres}")
        data = await fetch_json(
            "https://nominatim.openstreetmap.org/search",
            {"q": finall_addres, "format": "json", "limit": 1, "accept-language": "ru"},
        )
        if not data:
            print("Адрес не найден.")
            return

        lat, lon = data[0]["lat"], data[0]["lon"]
        print(f"Широта: {lat}, Долгота: {lon}")
        await save_address(finall_addres, data[0]["display_name"], float(lat), float(lon))
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

    query = f"{lat} {lon}"

    cached = await get_cached_address(query)
    if cached:
        print(f"[Кеш]\nАдрес: {cached.full_address}")
        return

    try:
        data = await fetch_json(
            "https://nominatim.openstreetmap.org/reverse",
            {"lat": lat, "lon": lon, "format": "json", "accept-language": "ru"},
        )
        address = data.get("display_name")
        if not address:
            print("Адрес по координатам не найден.")
            return

        print(f"Адрес: {address}")
        await save_address(query, address, lat, lon)
    except Exception as e:
        print(f"Ошибка запроса: {e}")
