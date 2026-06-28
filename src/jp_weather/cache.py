import json
import sqlite3
import threading
import time
from pathlib import Path
from platformdirs import user_cache_dir

class SQLiteCache:
    def __init__(self, expiration_seconds: int = 900):  # Default 15 minutes
        self.expiration_seconds = expiration_seconds
        cache_dir = Path(user_cache_dir("jp_weather"))
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = cache_dir / "cache.db"
        # Persistent connection for the lifetime of the cache instance
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        # Ensure the cache table exists using the persistent connection
        with self.lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    expires_at REAL
                )
            """)
            self.conn.commit()

    def get(self, key: str):
        # Retrieve a cached value if it exists and is not expired.
        self.clean_expired()
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT value FROM cache WHERE key = ? AND expires_at > ?", (key, time.time()))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
        return None

    def set(self, key: str, value, custom_expiry: int = None):
        expiry = custom_expiry if custom_expiry is not None else self.expiration_seconds
        expires_at = time.time() + expiry
        val_str = json.dumps(value)
        with self.lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
                (key, val_str, expires_at)
            )
            self.conn.commit()

    def clean_expired(self):
        # Remove any entries that have passed their expiry time.
        with self.lock:
            self.conn.execute("DELETE FROM cache WHERE expires_at <= ?", (time.time(),))
            self.conn.commit()

    def clear(self):
        # Empty the entire cache.
        with self.lock:
            self.conn.execute("DELETE FROM cache")
            self.conn.commit()
