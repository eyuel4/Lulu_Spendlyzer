#!/usr/bin/env python3
"""
Redis Setup Script for Lulu Spendlyzer
This script helps you set up Redis for development
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def print_header():
    print("🚀 Redis Setup for Lulu Spendlyzer")
    print("=" * 50)

def check_redis_installed():
    """Check if Redis is already installed and running"""
    try:
        result = subprocess.run(['redis-cli', 'ping'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and 'PONG' in result.stdout:
            print("✅ Redis is already running!")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return False

def install_redis_windows():
    """Install Redis on Windows"""
    print("📦 Installing Redis on Windows...")
    
    # Option 1: Using Chocolatey
    try:
        print("Trying Chocolatey installation...")
        subprocess.run(['choco', 'install', 'redis-64'], check=True)
        print("✅ Redis installed via Chocolatey")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Chocolatey not found or installation failed")
    
    # Option 2: Manual download
    print("\n📥 Manual Installation Required:")
    print("1. Download Redis for Windows from: https://github.com/microsoftarchive/redis/releases")
    print("2. Extract to C:\\Redis")
    print("3. Add C:\\Redis to your PATH")
    print("4. Run: redis-server")
    
    return False

def install_redis_macos():
    """Install Redis on macOS"""
    print("📦 Installing Redis on macOS...")
    try:
        subprocess.run(['brew', 'install', 'redis'], check=True)
        subprocess.run(['brew', 'services', 'start', 'redis'], check=True)
        print("✅ Redis installed and started via Homebrew")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Homebrew not found or installation failed")
        return False

def install_redis_linux():
    """Install Redis on Linux"""
    print("📦 Installing Redis on Linux...")
    
    # Detect package manager
    if os.path.exists('/etc/debian_version'):
        # Debian/Ubuntu
        try:
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'redis-server'], check=True)
            subprocess.run(['sudo', 'systemctl', 'start', 'redis-server'], check=True)
            subprocess.run(['sudo', 'systemctl', 'enable', 'redis-server'], check=True)
            print("✅ Redis installed and started via apt")
            return True
        except subprocess.CalledProcessError:
            print("❌ apt installation failed")
            return False
    elif os.path.exists('/etc/redhat-release'):
        # RHEL/CentOS/Fedora
        try:
            subprocess.run(['sudo', 'yum', 'install', '-y', 'redis'], check=True)
            subprocess.run(['sudo', 'systemctl', 'start', 'redis'], check=True)
            subprocess.run(['sudo', 'systemctl', 'enable', 'redis'], check=True)
            print("✅ Redis installed and started via yum")
            return True
        except subprocess.CalledProcessError:
            print("❌ yum installation failed")
            return False
    else:
        print("❌ Unsupported Linux distribution")
        return False

def test_redis_connection():
    """Test Redis connection"""
    print("\n🔍 Testing Redis connection...")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis connection successful!")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

def create_env_file():
    """Create or update .env file with Redis configuration"""
    env_file = Path('.env')
    
    if env_file.exists():
        content = env_file.read_text()
        if 'REDIS_URL' not in content:
            content += '\nREDIS_URL=redis://localhost:6379\n'
            env_file.write_text(content)
            print("✅ Added REDIS_URL to existing .env file")
    else:
        env_file.write_text('REDIS_URL=redis://localhost:6379\n')
        print("✅ Created .env file with REDIS_URL")

def main():
    print_header()
    
    # Check if Redis is already running
    if check_redis_installed():
        create_env_file()
        if test_redis_connection():
            print("\n🎉 Redis is ready to use!")
            return
    
    # Install Redis based on platform
    system = platform.system().lower()
    
    if system == 'windows':
        success = install_redis_windows()
    elif system == 'darwin':  # macOS
        success = install_redis_macos()
    elif system == 'linux':
        success = install_redis_linux()
    else:
        print(f"❌ Unsupported operating system: {system}")
        return
    
    if success:
        create_env_file()
        if test_redis_connection():
            print("\n🎉 Redis setup completed successfully!")
        else:
            print("\n⚠️  Redis installed but connection test failed")
            print("Please start Redis manually and try again")
    else:
        print("\n❌ Redis installation failed")
        print("Please install Redis manually and try again")

if __name__ == "__main__":
    main() 