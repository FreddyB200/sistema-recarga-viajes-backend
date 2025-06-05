from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db, get_redis_client
from typing import Dict, Any
import redis
import time
import asyncio

router = APIRouter(prefix="/api/v1/cache", tags=["cache"])


@router.get("/stats")
def get_cache_stats(redis_client: redis.Redis = Depends(get_redis_client)):
    """
    Get Redis cache statistics
    """
    try:
        info = redis_client.info()
        
        # Extract relevant stats
        stats = {
            "redis_version": info.get("redis_version", "Unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory": info.get("used_memory", 0),
            "used_memory_human": info.get("used_memory_human", "0B"),
            "used_memory_peak": info.get("used_memory_peak", 0),
            "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
            "total_connections_received": info.get("total_connections_received", 0),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "uptime_in_seconds": info.get("uptime_in_seconds", 0),
        }
        
        # Calculate hit rate
        hits = stats["keyspace_hits"]
        misses = stats["keyspace_misses"]
        total_requests = hits + misses
        hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0
        
        stats["hit_rate_percentage"] = round(hit_rate, 2)
        stats["total_cache_requests"] = total_requests
        
        return {"cache_stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache stats: {str(e)}")


@router.get("/keys")
def get_cache_keys(redis_client: redis.Redis = Depends(get_redis_client)):
    """
    Get information about cached keys
    """
    try:
        # Get all keys with their TTL
        keys = redis_client.keys("*")
        key_info = []
        
        for key in keys:
            key_str = key.decode('utf-8') if isinstance(key, bytes) else str(key)
            ttl = redis_client.ttl(key)
            key_type = redis_client.type(key).decode('utf-8') if redis_client.type(key) else "unknown"
            
            try:
                size = redis_client.memory_usage(key) if hasattr(redis_client, 'memory_usage') else 0
            except:
                size = 0
            
            key_info.append({
                "key": key_str,
                "type": key_type,
                "ttl": ttl,  # -1 means no expiry, -2 means key doesn't exist
                "size_bytes": size
            })
        
        # Sort by key name
        key_info.sort(key=lambda x: x["key"])
        
        return {
            "total_keys": len(key_info),
            "keys": key_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache keys: {str(e)}")


@router.post("/clear")
def clear_cache(redis_client: redis.Redis = Depends(get_redis_client)):
    """
    Clear all cache entries (use with caution)
    """
    try:
        keys_before = len(redis_client.keys("*"))
        redis_client.flushdb()
        
        return {
            "message": "Cache cleared successfully",
            "keys_cleared": keys_before
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")


@router.delete("/key/{key_name}")
def delete_cache_key(key_name: str, redis_client: redis.Redis = Depends(get_redis_client)):
    """
    Delete a specific cache key
    """
    try:
        result = redis_client.delete(key_name)
        
        if result == 1:
            return {"message": f"Key '{key_name}' deleted successfully"}
        else:
            return {"message": f"Key '{key_name}' not found or already deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting cache key: {str(e)}")


@router.get("/performance-test")
async def cache_performance_test(
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Run a simple performance test to demonstrate cache benefits
    """
    try:
        # Test endpoint: /api/v1/trips/total
        test_key = "trips:total"
        
        # Clear the test key to ensure we test both scenarios
        redis_client.delete(test_key)
        
        # Test 1: Database query (cache miss)
        start_time = time.time()
        from sqlalchemy import text
        result = db.execute(text("SELECT COUNT(*) FROM trips")).scalar()
        db_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Simulate caching the result
        import json
        cache_data = {"total_trips": result}
        redis_client.setex(test_key, 300, json.dumps(cache_data))
        
        # Test 2: Cache query (cache hit)
        start_time = time.time()
        cached_result = redis_client.get(test_key)
        cached_data = json.loads(cached_result) if cached_result else None
        cache_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Calculate improvement
        improvement = (db_time / cache_time) if cache_time > 0 else 0
        
        return {
            "performance_test": {
                "database_query_time_ms": round(db_time, 3),
                "cache_query_time_ms": round(cache_time, 3),
                "performance_improvement": f"{improvement:.1f}x faster",
                "time_saved_ms": round(db_time - cache_time, 3),
                "test_data": cache_data
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running performance test: {str(e)}")


@router.get("/health")
def cache_health_check(redis_client: redis.Redis = Depends(get_redis_client)):
    """
    Check cache health and connectivity
    """
    try:
        # Test basic connectivity
        start_time = time.time()
        redis_client.ping()
        ping_time = (time.time() - start_time) * 1000
        
        # Test set/get operations
        test_key = "health_check_test"
        test_value = "ok"
        
        start_time = time.time()
        redis_client.setex(test_key, 10, test_value)
        retrieved_value = redis_client.get(test_key)
        operation_time = (time.time() - start_time) * 1000
        
        # Clean up
        redis_client.delete(test_key)
        
        is_healthy = retrieved_value.decode('utf-8') == test_value if retrieved_value else False
        
        return {
            "cache_health": {
                "status": "healthy" if is_healthy else "unhealthy",
                "ping_time_ms": round(ping_time, 3),
                "operation_time_ms": round(operation_time, 3),
                "connectivity": "ok" if is_healthy else "failed"
            }
        }
    except Exception as e:
        return {
            "cache_health": {
                "status": "unhealthy",
                "error": str(e),
                "connectivity": "failed"
            }
        } 