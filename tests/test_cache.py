import time
import pytest
from jptrain.cache import SQLiteCache

def test_cache_set_get():
    cache = SQLiteCache(expiration_seconds=10)
    cache.clear()
    
    cache.set("test_key", {"foo": "bar"})
    val = cache.get("test_key")
    assert val == {"foo": "bar"}

def test_cache_expiration():
    cache = SQLiteCache(expiration_seconds=1)
    cache.clear()
    
    cache.set("test_expire", "some_value")
    # Retrieve immediately
    assert cache.get("test_expire") == "some_value"
    
    # Wait for expiration
    time.sleep(1.1)
    assert cache.get("test_expire") is None

def test_cache_custom_expiry():
    cache = SQLiteCache(expiration_seconds=1)
    cache.clear()
    
    cache.set("test_custom", "custom_value", custom_expiry=5)
    # Check after 1.1s, should still exist since custom expiry is 5s
    time.sleep(1.1)
    assert cache.get("test_custom") == "custom_value"

def test_cache_clear():
    cache = SQLiteCache(expiration_seconds=10)
    cache.clear()
    
    cache.set("k1", "v1")
    cache.set("k2", "v2")
    
    cache.clear()
    assert cache.get("k1") is None
    assert cache.get("k2") is None
