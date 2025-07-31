import asyncio
import os
from pathlib import Path
from sqlalchemy import text

# Add the project root to Python path
project_root = Path(__file__).parent
import sys
sys.path.insert(0, str(project_root))

from app.core.database import engine, DATABASE_URL

async def test_connection():
    print(f"Database URL: {DATABASE_URL}")
    print(f"Current working directory: {os.getcwd()}")
    
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = result.fetchall()
            print(f"Tables found: {len(tables)}")
            for table in tables:
                print(f"  - {table[0]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection()) 