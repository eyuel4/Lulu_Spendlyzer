import os
from dotenv import load_dotenv

def test_env_loading():
    # Load .env file
    load_dotenv()
    db_url = os.getenv('DB_URL')
    assert db_url is not None and db_url != '', 'DB_URL should be set in .env and not empty'
    print('DB_URL:', db_url)

def test_google_oauth_env():
    load_dotenv()
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    assert client_id is not None and client_id != '', 'GOOGLE_CLIENT_ID should be set in .env and not empty'
    assert client_secret is not None and client_secret != '', 'GOOGLE_CLIENT_SECRET should be set in .env and not empty'
    print('GOOGLE_CLIENT_ID:', client_id)
    print('GOOGLE_CLIENT_SECRET:', client_secret) 