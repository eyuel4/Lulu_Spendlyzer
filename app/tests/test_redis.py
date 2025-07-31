#!/usr/bin/env python3
"""
Test Redis Caching Implementation
"""

import asyncio
import json
from app.core.cache import RedisCache, CacheKeys

async def test_redis_connection():
    """Test basic Redis connection"""
    print("🔍 Testing Redis Connection...")
    
    try:
        cache = RedisCache()
        redis = await cache.get_redis()
        await redis.ping()
        print("✅ Redis connection successful!")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

async def test_basic_caching():
    """Test basic cache operations"""
    print("\n🔍 Testing Basic Caching...")
    
    try:
        cache = RedisCache()
        
        # Test set and get
        test_data = {"user_id": 123, "name": "John Doe", "email": "john@example.com"}
        await cache.set("test_user", test_data, expire=60)
        print("✅ Data set in cache")
        
        # Test get
        retrieved_data = await cache.get("test_user")
        if retrieved_data == test_data:
            print("✅ Data retrieved from cache successfully")
        else:
            print("❌ Data retrieval failed")
            return False
        
        # Test delete
        await cache.delete("test_user")
        deleted_data = await cache.get("test_user")
        if deleted_data is None:
            print("✅ Data deleted from cache successfully")
        else:
            print("❌ Data deletion failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Basic caching test failed: {e}")
        return False

async def test_cache_keys():
    """Test cache key generation"""
    print("\n🔍 Testing Cache Keys...")
    
    try:
        # Test user keys
        user_key = CacheKeys.user(123)
        print(f"User key: {user_key}")
        
        # Test user preferences key
        prefs_key = CacheKeys.user_preferences(123)
        print(f"User preferences key: {prefs_key}")
        
        # Test transaction keys
        trans_key = CacheKeys.transactions(123)
        print(f"Transactions key: {trans_key}")
        
        trans_month_key = CacheKeys.transactions(123, "2024-01")
        print(f"Transactions by month key: {trans_month_key}")
        
        # Test family keys
        family_key = CacheKeys.family_group(456)
        print(f"Family group key: {family_key}")
        
        members_key = CacheKeys.family_members(456)
        print(f"Family members key: {members_key}")
        
        print("✅ Cache key generation successful!")
        return True
        
    except Exception as e:
        print(f"❌ Cache key test failed: {e}")
        return False

async def test_cache_expiration():
    """Test cache expiration"""
    print("\n🔍 Testing Cache Expiration...")
    
    try:
        cache = RedisCache()
        
        # Set data with short expiration
        test_data = {"message": "This will expire soon"}
        await cache.set("expire_test", test_data, expire=2)  # 2 seconds
        print("✅ Data set with 2-second expiration")
        
        # Check it exists
        data = await cache.get("expire_test")
        if data:
            print("✅ Data exists immediately after setting")
        else:
            print("❌ Data not found immediately after setting")
            return False
        
        # Wait for expiration
        print("⏳ Waiting for expiration...")
        await asyncio.sleep(3)
        
        # Check if expired
        expired_data = await cache.get("expire_test")
        if expired_data is None:
            print("✅ Data expired successfully")
        else:
            print("❌ Data did not expire")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Cache expiration test failed: {e}")
        return False

async def test_cache_patterns():
    """Test cache pattern operations"""
    print("\n🔍 Testing Cache Patterns...")
    
    try:
        cache = RedisCache()
        
        # Set multiple keys with pattern
        await cache.set("user:123:profile", {"name": "John"}, expire=60)
        await cache.set("user:123:preferences", {"theme": "dark"}, expire=60)
        await cache.set("user:123:transactions", {"count": 10}, expire=60)
        await cache.set("user:456:profile", {"name": "Jane"}, expire=60)
        
        print("✅ Multiple keys set with pattern")
        
        # Test pattern deletion
        deleted_count = await cache.delete_pattern("user:123:*")
        print(f"✅ Deleted {deleted_count} keys with pattern 'user:123:*'")
        
        # Verify deletion
        remaining_123 = await cache.get("user:123:profile")
        remaining_456 = await cache.get("user:456:profile")
        
        if remaining_123 is None and remaining_456 is not None:
            print("✅ Pattern deletion worked correctly")
        else:
            print("❌ Pattern deletion failed")
            return False
        
        # Clean up
        await cache.delete_pattern("user:*")
        
        return True
        
    except Exception as e:
        print(f"❌ Cache pattern test failed: {e}")
        return False

async def test_performance():
    """Test cache performance"""
    print("\n🔍 Testing Cache Performance...")
    
    try:
        cache = RedisCache()
        
        # Test multiple operations
        import time
        start_time = time.time()
        
        # Set 100 items
        for i in range(100):
            await cache.set(f"perf_test_{i}", {"id": i, "data": f"test_data_{i}"}, expire=60)
        
        set_time = time.time() - start_time
        print(f"✅ Set 100 items in {set_time:.3f} seconds")
        
        # Get 100 items
        start_time = time.time()
        for i in range(100):
            await cache.get(f"perf_test_{i}")
        
        get_time = time.time() - start_time
        print(f"✅ Retrieved 100 items in {get_time:.3f} seconds")
        
        # Clean up
        await cache.delete_pattern("perf_test_*")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Redis Caching Test Suite")
    print("=" * 50)
    
    tests = [
        test_redis_connection,
        test_basic_caching,
        test_cache_keys,
        test_cache_expiration,
        test_cache_patterns,
        test_performance
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if await test():
                passed += 1
            else:
                print(f"❌ Test {test.__name__} failed")
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Redis caching is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the Redis setup.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main()) 