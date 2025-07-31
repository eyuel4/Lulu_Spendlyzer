#!/usr/bin/env python3
"""
Download and Setup Redis for Windows
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
from pathlib import Path

def download_file(url, filename):
    """Download a file with progress"""
    print(f"📥 Downloading {filename}...")
    urllib.request.urlretrieve(url, filename)
    print(f"✅ Downloaded {filename}")

def extract_zip(zip_path, extract_to):
    """Extract zip file"""
    print(f"📦 Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print(f"✅ Extracted to {extract_to}")

def setup_redis_windows():
    """Setup Redis for Windows"""
    redis_dir = Path("redis-windows")
    
    if redis_dir.exists():
        print("✅ Redis directory already exists")
        return redis_dir
    
    # Create Redis directory
    redis_dir.mkdir(exist_ok=True)
    
    # Download Redis for Windows
    redis_url = "https://github.com/microsoftarchive/redis/releases/download/win-3.0.504/Redis-x64-3.0.504.zip"
    zip_file = "redis-windows.zip"
    
    try:
        download_file(redis_url, zip_file)
        extract_zip(zip_file, redis_dir)
        
        # Clean up zip file
        os.remove(zip_file)
        
        print("✅ Redis for Windows downloaded and extracted")
        return redis_dir
        
    except Exception as e:
        print(f"❌ Error downloading Redis: {e}")
        return None

def start_redis_server(redis_dir):
    """Start Redis server"""
    redis_exe = redis_dir / "redis-server.exe"
    
    if not redis_exe.exists():
        print(f"❌ Redis server not found at {redis_exe}")
        return False
    
    print("🚀 Starting Redis server...")
    try:
        # Start Redis server in background
        process = subprocess.Popen(
            [str(redis_exe)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=redis_dir
        )
        
        # Wait a moment for server to start
        import time
        time.sleep(2)
        
        # Test connection
        if test_redis_connection():
            print("✅ Redis server started successfully!")
            return True
        else:
            print("❌ Redis server failed to start")
            return False
            
    except Exception as e:
        print(f"❌ Error starting Redis: {e}")
        return False

def test_redis_connection():
    """Test Redis connection"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=5)
        r.ping()
        return True
    except:
        return False

def main():
    print("🚀 Redis Setup for Windows")
    print("=" * 40)
    
    # Check if Redis is already running
    if test_redis_connection():
        print("✅ Redis is already running!")
        return True
    
    # Setup Redis
    redis_dir = setup_redis_windows()
    if not redis_dir:
        return False
    
    # Start Redis server
    if start_redis_server(redis_dir):
        print("\n🎉 Redis is ready to use!")
        print(f"📁 Redis files: {redis_dir}")
        print("🔧 To start Redis manually: redis-server.exe")
        return True
    else:
        print("\n❌ Failed to start Redis")
        return False

if __name__ == "__main__":
    main() 