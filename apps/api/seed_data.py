import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.user import User

async def seed():
    async with AsyncSessionLocal() as session:
        # Check if user exists
        from sqlalchemy.future import select
        result = await session.execute(select(User).where(User.email == "admin@octet.com"))
        user = result.scalars().first()
        if not user:
            user = User(email="admin@octet.com", role="admin")
            session.add(user)
            await session.commit()
            print("Seed data inserted successfully.")
        else:
            print("Seed data already exists.")

if __name__ == "__main__":
    asyncio.run(seed())
