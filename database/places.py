from sqlalchemy import select
from database.models import async_session, Place


async def get_cached_places(address_query: str):
    async with async_session() as session:
        result = await session.execute(
            select(Place).where(Place.address_query == address_query)
        )
        return result.scalars().all()


async def save_places(address_query: str, places: list[dict]):
    async with async_session() as session:
        async with session.begin():
            for place in places:
                session.add(
                    Place(
                        address_query=address_query,
                        name=place["name"],
                        category=place["category"],
                        latitude=place["lat"],
                        longitude=place["lon"],
                    )
                )
