from titiler.xarray.settings import ApiSettings
import fakeredis
import os
import redis

api_settings = ApiSettings()

class RedisCache:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            if os.getenv('TEST_ENVIRONMENT'):
                server = fakeredis.FakeServer()
                # Use fakeredis in a test environment
                cls._instance = fakeredis.FakeStrictRedis(server=server)
            else:
                # Use real Redis in other environments
                cls._instance = redis.StrictRedis(host=api_settings.cache_host, port=6379, db=0)
        return cls._instance

def get_redis():
  pool = RedisCache.get_instance()
  # Here, we re-use our connection pool
  # not creating a new one
  return redis.Redis(connection_pool=pool)
