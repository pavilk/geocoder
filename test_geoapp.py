import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from database.models import Address, init_db
from database.cache import get_cached_address, save_address
from services.geocoder import handle_address_input, handle_coordinates_input


@pytest.fixture(scope="module", autouse=True)
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module", autouse=True)
async def setup_db():
    await init_db()


@pytest.fixture
async def address_obj():
    address = Address(
        input_query="Тестовый адрес",
        full_address="Тестовый адрес, Россия",
        latitude=55.0,
        longitude=37.0,
    )
    await save_address(address.input_query, address.full_address, address.latitude, address.longitude)
    return address


# Тесты кеша

@pytest.mark.asyncio
async def test_save_and_get_cached_address():
    query = "Test query"
    await save_address(query, "Test full address", 55.5, 37.5)
    cached = await get_cached_address(query)
    assert cached is not None
    assert cached.input_query == query
    assert cached.latitude == 55.5


# Моки Dadata + Nominatim

@pytest.mark.asyncio
@patch("services.geocoder.input", side_effect=["Москва", "Тверская", "10"])
@patch("services.geocoder.clean_address")
@patch("services.geocoder.fetch_json")
@patch("services.geocoder.save_address", new_callable=AsyncMock)
@patch("services.geocoder.get_cached_address", new_callable=AsyncMock, return_value=None)
async def test_handle_address_input_success(
    mock_cache, mock_save, mock_fetch, mock_clean, mock_input
):
    mock_clean.return_value = {"result": "Москва, Тверская 10"}
    mock_fetch.return_value = [{
        "lat": "55.7558", "lon": "37.6176", "display_name": "Москва, Тверская, 10"
    }]

    await handle_address_input()

    mock_clean.assert_called_once()
    mock_fetch.assert_called_once()
    mock_save.assert_awaited_once()


@pytest.mark.asyncio
@patch("services.geocoder.input", return_value="55.75 37.61")
@patch("services.geocoder.fetch_json")
@patch("services.geocoder.save_address", new_callable=AsyncMock)
@patch("services.geocoder.get_cached_address", new_callable=AsyncMock, return_value=None)
async def test_handle_coordinates_input_success(mock_cache, mock_save, mock_fetch, mock_input):
    mock_fetch.return_value = {
        "display_name": "Москва, Россия"
    }

    await handle_coordinates_input()

    mock_fetch.assert_called_once()
    mock_save.assert_awaited_once()


@pytest.mark.asyncio
@patch("services.geocoder.input", return_value="ошибка данные")
async def test_handle_coordinates_input_invalid(mock_input):
    await handle_coordinates_input()  # Должно просто напечатать ошибку и выйти без исключения