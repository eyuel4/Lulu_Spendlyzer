"""Test script to verify Plaid routes are accessible"""
import asyncio
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_plaid_routes():
    """Test if Plaid routes are accessible"""
    print("Testing Plaid routes...")
    print(f"Total routes in app: {len(app.routes)}")
    
    # List all Plaid routes
    plaid_routes = [r for r in app.routes if hasattr(r, 'path') and 'plaid' in r.path]
    print(f"\nFound {len(plaid_routes)} Plaid routes:")
    for route in plaid_routes:
        methods = list(route.methods) if hasattr(route, 'methods') else []
        print(f"  {route.path} {methods}")
    
    # Test the test endpoint
    print("\nTesting GET /plaid/test...")
    response = client.get("/plaid/test")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Test create-link-token (will fail auth, but should not be 404)
    print("\nTesting POST /plaid/create-link-token (without auth)...")
    response = client.post("/plaid/create-link-token", json={})
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")

if __name__ == "__main__":
    test_plaid_routes()

