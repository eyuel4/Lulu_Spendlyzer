#!/usr/bin/env python3
"""
Migration script to add family_name column to family_groups table.
Run this script to update existing databases.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
env_path = project_root / 'app' / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    root_env_path = project_root / '.env'
    if root_env_path.exists():
        load_dotenv(dotenv_path=root_env_path)

async def migrate_family_name():
    """Add family_name column to family_groups table if it doesn't exist."""
    db_url = os.getenv('DB_URL')
    if not db_url:
        print("Error: DB_URL environment variable not set")
        return
    
    engine = create_async_engine(db_url)
    
    async with engine.begin() as conn:
        # Check if family_name column already exists
        result = await conn.execute(text("""
            SELECT name FROM pragma_table_info('family_groups') 
            WHERE name = 'family_name'
        """))
        
        if result.fetchone():
            print("family_name column already exists in family_groups table")
        else:
            # Add the family_name column
            await conn.execute(text("""
                ALTER TABLE family_groups 
                ADD COLUMN family_name TEXT NOT NULL DEFAULT 'Family Group'
            """))
            print("Added family_name column to family_groups table")
    
    await engine.dispose()

if __name__ == "__main__":
    print("Running migration to add family_name column...")
    asyncio.run(migrate_family_name())
    print("Migration completed.") 