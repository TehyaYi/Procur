# test_env.py
from procur.core.config import get_settings
import os

print("🔧 Testing environment configuration...")
print(f"Current working directory: {os.getcwd()}")
print(f".env file exists: {os.path.exists('.env')}")

if os.path.exists('.env'):
    with open('.env', 'r') as f:
        lines = f.readlines()
        print(f".env file has {len(lines)} lines")

try:
    settings = get_settings()
    print(f"FIREBASE_PROJECT_ID: {settings.FIREBASE_PROJECT_ID}")
    print(f"FIREBASE_CREDENTIALS_PATH: {settings.FIREBASE_CREDENTIALS_PATH}")
    print(f"Credentials file exists: {os.path.exists(settings.FIREBASE_CREDENTIALS_PATH)}")
    
    if os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
        import json
        with open(settings.FIREBASE_CREDENTIALS_PATH, 'r') as f:
            cred_data = json.load(f)
            print(f"Credentials project_id: {cred_data.get('project_id')}")
    
except Exception as e:
    print(f"Error loading settings: {e}")
