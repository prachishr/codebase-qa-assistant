
import asyncio

from backend.app.db.database import Base, engine
from backend.app.models import User, Repository, Conversation, Message


async def create_tables():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    print("All database tables created successfully!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_tables())
