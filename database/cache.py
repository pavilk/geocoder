from .models import async_session, Address
from sqlalchemy import select


async def get_cached_address(query: str):
    async with async_session() as session:
        result = await session.execute(select(Address).where(Address.input_query == query))
        return result.scalar_one_or_none()


async def save_address(query: str, full_address: str, lat: float, lon: float):
    async with async_session() as session:
        async with session.begin():
            session.add(Address(
                input_query=query,
                full_address=full_address,
                latitude=lat,
                longitude=lon,
            ))
