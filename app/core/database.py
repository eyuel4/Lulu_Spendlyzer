import os
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from dotenv import load_dotenv
from sqlalchemy import Column, Integer

# Get the project root directory
project_root = Path(__file__).parent.parent.parent

# Load .env file from the correct location
env_path = project_root / 'app' / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Try root directory
    root_env_path = project_root / '.env'
    if root_env_path.exists():
        load_dotenv(dotenv_path=root_env_path)

# Import all models to ensure SQLAlchemy can create tables and resolve relationships
from app.models.base import Base
from app.models.user import User
from app.models.family_group import FamilyGroup
from app.models.card import Card
from app.models.transaction import Transaction
from app.models.category_override import CategoryOverride
from app.models.report import Report
from app.models.grocery_category import GroceryCategory
from app.models.shopping_category import ShoppingCategory
from app.models.system_log import SystemLog, AuditLog

DATABASE_URL = os.getenv("DB_URL")
if not DATABASE_URL:
    raise RuntimeError("DB_URL environment variable must be set")

# Ensure the database path is absolute and points to the working directory
if DATABASE_URL.startswith('sqlite+aiosqlite:///'):
    db_path = DATABASE_URL.replace('sqlite+aiosqlite:///', '')
    if db_path.startswith('./') or db_path.startswith('../'):
        # Use absolute path in project root directory
        DATABASE_URL = f'sqlite+aiosqlite:///{project_root}/finance.db'

engine = create_async_engine(
    DATABASE_URL, echo=True
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# Async function to create all tables
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Dependency for FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session 