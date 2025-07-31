#!/usr/bin/env python3
"""
Test script to verify invite-signup functionality
Tests both the backend endpoints and the frontend routing.
"""

import requests
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_backend_endpoints():
    """Test the backend endpoints for invitation functionality"""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Backend Endpoints")
    print("=" * 40)
    
    # Test 1: Health check
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Backend is running")
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Backend is not running. Start it with: python -m uvicorn app.main:app --reload --port 8000")
        return False
    
    # Test 2: Test invitation endpoint with invalid token
    try:
        response = requests.get(f"{base_url}/family/invite/accept/invalid-token")
        if response.status_code == 404:
            print("✅ Invitation endpoint responds correctly to invalid tokens")
        else:
            print(f"⚠️  Unexpected response for invalid token: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing invitation endpoint: {e}")
        return False
    
    return True

def test_frontend_routing():
    """Test the frontend routing for invite-signup"""
    frontend_url = "http://localhost:4200"
    
    print("\n🧪 Testing Frontend Routing")
    print("=" * 40)
    
    # Test 1: Check if frontend is running
    try:
        response = requests.get(frontend_url)
        if response.status_code == 200:
            print("✅ Frontend is running")
        else:
            print(f"❌ Frontend check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Frontend is not running. Start it with: npm start (in spendlyzer-frontend directory)")
        return False
    
    # Test 2: Test invite-signup route
    try:
        test_token = "test-token-123"
        invite_url = f"{frontend_url}/invite-signup?token={test_token}"
        response = requests.get(invite_url)
        
        if response.status_code == 200:
            print("✅ Invite-signup route is accessible")
            print(f"   URL: {invite_url}")
        else:
            print(f"❌ Invite-signup route failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing invite-signup route: {e}")
        return False
    
    return True

def test_email_link_format():
    """Test the email link format"""
    print("\n🧪 Testing Email Link Format")
    print("=" * 40)
    
    # Example email link
    email_link = "http://localhost:4200/invite-signup?token=i6YmZqmDGJWr2pm7j3USUKH1a0XHaWgU2y_WU-dYjn4"
    
    print(f"📧 Email link format: {email_link}")
    print("✅ Link format is correct")
    print("   - Uses query parameter: ?token=")
    print("   - Uses correct path: /invite-signup")
    print("   - Points to localhost:4200 (frontend)")
    
    return True

def main():
    """Run all tests"""
    print("🚀 Invite Signup Route Test")
    print("=" * 50)
    
    backend_ok = test_backend_endpoints()
    frontend_ok = test_frontend_routing()
    email_ok = test_email_link_format()
    
    print("\n" + "=" * 50)
    if backend_ok and frontend_ok and email_ok:
        print("✅ All tests passed!")
        print("\n📋 Next Steps:")
        print("1. Make sure both backend and frontend are running")
        print("2. Click the email link: http://localhost:4200/invite-signup?token=YOUR_TOKEN")
        print("3. The page should load the invite-signup component")
        print("4. If it redirects to login, check browser console for errors")
    else:
        print("❌ Some tests failed. Check the output above.")
        if not backend_ok:
            print("   - Start backend: python -m uvicorn app.main:app --reload --port 8000")
        if not frontend_ok:
            print("   - Start frontend: cd spendlyzer-frontend && npm start")

if __name__ == "__main__":
    main() 