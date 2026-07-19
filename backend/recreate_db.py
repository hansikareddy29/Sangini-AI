import asyncio
from app.database.connection import engine, Base
from app.models.models import *

async def recreate():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        print("Database recreated successfully.")

if __name__ == "__main__":
    asyncio.run(recreate())
