from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from config import PASSWORD_DB

url = URL.create("postgresql+asyncpg", username="postgres", password=PASSWORD_DB, host="localhost", database="naurok")
engine = create_async_engine(url)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
