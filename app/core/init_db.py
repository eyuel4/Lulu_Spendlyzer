import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import traceback

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Change to project root directory to ensure database is created there
os.chdir(project_root)

# Load .env file from the correct location
env_path = project_root / 'app' / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Try root directory
    root_env_path = project_root / '.env'
    if root_env_path.exists():
        load_dotenv(dotenv_path=root_env_path)

# Ensure DB_URL points to the working directory
db_url = os.getenv('DB_URL')
if db_url and 'sqlite' in db_url:
    # Replace any relative path with absolute path in working directory
    if db_url.startswith('sqlite+aiosqlite:///'):
        db_path = db_url.replace('sqlite+aiosqlite:///', '')
        if db_path.startswith('./') or db_path.startswith('../'):
            # Use absolute path in working directory
            os.environ['DB_URL'] = f'sqlite+aiosqlite:///{project_root}/finance.db'

from app.core.database import init_db
import asyncio

# Import all models to register them with Base
from app.models import user, card, transaction, category_override, report, grocery_category, shopping_category, SystemLog, AuditLog
from app.models.family_group import FamilyGroup
from app.models.invitation import Invitation
from app.models.user_session import UserSession
from app.models.trusted_device import TrustedDevice
from app.models.two_factor_auth import TwoFactorAuth, TwoFactorBackupCode
from app.models.notification_settings import NotificationSettings
from app.models.privacy_settings import PrivacySettings
# UserPreferences is imported via the user module

if __name__ == "__main__":
    try:
        print("[DEBUG] Entered __main__ block.")
        print("Creating all tables...")
        print(f"Working directory: {os.getcwd()}")
        print(f"DB_URL: {os.getenv('DB_URL')}")
        asyncio.run(init_db())
        print("All tables created.")
    except Exception as e:
        print("[ERROR] Exception occurred during DB initialization:")
        traceback.print_exc() 