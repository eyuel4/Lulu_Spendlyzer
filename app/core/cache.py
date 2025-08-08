import os
import json
import pickle
import logging
import redis.asyncio as redis
from typing import Any, Optional, Union
from datetime import timedelta

logger = logging.getLogger(__name__)

# Global cache instance
cache = None

class RedisCache:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self.db = db
        self._redis = None
        self._connection_failed = False

    async def get_redis(self) -> redis.Redis:
        """Get Redis connection"""
        if self._connection_failed:
            raise ConnectionError("Redis connection previously failed")
            
        if self._redis is None:
            try:
                self._redis = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                await self._redis.ping()
                logger.info(f"Connected to Redis at {self.host}:{self.port}")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._connection_failed = True
                raise
        return self._redis

    async def set(self, key: str, value: Any, expire: Union[int, timedelta] = 3600, use_pickle: bool = False) -> bool:
        """Set a value in cache"""
        try:
            redis_client = await self.get_redis()
            
            if use_pickle:
                serialized_value = pickle.dumps(value)
            else:
                serialized_value = json.dumps(value, default=str)
            
            if isinstance(expire, timedelta):
                expire_seconds = int(expire.total_seconds())
            else:
                expire_seconds = expire
            
            await redis_client.setex(key, expire_seconds, serialized_value)
            logger.debug(f"Cache SET: {key} (expires in {expire_seconds}s)")
            return True
            
        except Exception as e:
            logger.error(f"Cache SET error for key {key}: {e}")
            return False

    async def get(self, key: str, use_pickle: bool = False) -> Optional[Any]:
        """Get a value from cache"""
        try:
            redis_client = await self.get_redis()
            value = await redis_client.get(key)
            
            if value is None:
                logger.debug(f"Cache MISS: {key}")
                return None
            
            if use_pickle:
                deserialized_value = pickle.loads(value.encode('latin1'))
            else:
                deserialized_value = json.loads(value)
            
            logger.debug(f"Cache HIT: {key}")
            return deserialized_value
            
        except Exception as e:
            logger.error(f"Cache GET error for key {key}: {e}")
            return None

    async def delete(self, key: str) -> bool:
        """Delete a key from cache"""
        try:
            redis_client = await self.get_redis()
            result = await redis_client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return result > 0
            
        except Exception as e:
            logger.error(f"Cache DELETE error for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching a pattern"""
        try:
            redis_client = await self.get_redis()
            keys = await redis_client.keys(pattern)
            
            if keys:
                deleted = await redis_client.delete(*keys)
                logger.debug(f"Cache DELETE PATTERN: {pattern} ({deleted} keys)")
                return deleted
            return 0
            
        except Exception as e:
            logger.error(f"Cache DELETE PATTERN error for {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if a key exists"""
        try:
            redis_client = await self.get_redis()
            result = await redis_client.exists(key)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Cache EXISTS error for key {key}: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """Get time to live for a key"""
        try:
            redis_client = await self.get_redis()
            return await redis_client.ttl(key)
            
        except Exception as e:
            logger.error(f"Cache TTL error for key {key}: {e}")
            return -1

    async def flush_db(self) -> bool:
        """Clear all keys in current database"""
        try:
            redis_client = await self.get_redis()
            await redis_client.flushdb()
            logger.info("Cache flushed")
            return True
            
        except Exception as e:
            logger.error(f"Cache FLUSH error: {e}")
            return False

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis connection closed")

# Cache key management
class CacheKeys:
    @staticmethod
    def user(user_id: int) -> str:
        return f"user:{user_id}"
    
    @staticmethod
    def user_preferences(user_id: int) -> str:
        return f"user_preferences:{user_id}"
    
    @staticmethod
    def transactions(user_id: int, month: Optional[str] = None) -> str:
        if month:
            return f"transactions:{user_id}:{month}"
        return f"transactions:{user_id}"
    
    @staticmethod
    def family_group(family_id: int) -> str:
        return f"family_group:{family_id}"
    
    @staticmethod
    def family_members(family_id: int) -> str:
        return f"family_members:{family_id}"
    
    @staticmethod
    def reports(user_id: int, report_type: str, month: Optional[str] = None) -> str:
        if month:
            return f"reports:{user_id}:{report_type}:{month}"
        return f"reports:{user_id}:{report_type}"
    
    @staticmethod
    def transaction(transaction_id: int) -> str:
        return f"transaction:{transaction_id}"

# Cache decorator removed for now - will be reimplemented later

# Initialize global cache instance
def get_cache() -> RedisCache:
    """Get global cache instance"""
    global cache
    if cache is None:
        cache = RedisCache()
    return cache

# Cleanup function
async def cleanup_cache():
    """Cleanup cache connections"""
    global cache
    if cache:
        await cache.close()
        cache = None 