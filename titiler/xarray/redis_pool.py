""" Redis singleton class. """
import os

from titiler.xarray.settings import ApiSettings

api_settings = ApiSettings()

try:
    import redis
except ImportError:
    redis = None  # type: ignore

try:
    import fakeredis
except ImportError:
    fakeredis = None


class RedisCache:
    """Redis connection pool singleton class."""

    _instance = None

    @classmethod
    def get_instance(cls):
        """Get the redis connection pool."""

        assert (
            redis
        ), "`redis` must be installed to enable caching. Please install titiler-xarray with the `cache` optional dependencies that include `redis`."

        if cls._instance is None:
            cls._instance = redis.ConnectionPool(
                host=api_settings.cache_host, port=6379, db=0
            )
        return cls._instance


def get_redis():
    """Get a redis connection."""
    if os.getenv("TEST_ENVIRONMENT"):

        assert (
            fakeredis
        ), "`fakeredis` must be installed to enable caching in test environment. Please install titiler-xarray with the `dev` optional dependencies that include `fakeredis`."

        server = fakeredis.FakeServer()
        # Use fakeredis in a test environment
        return fakeredis.FakeRedis(server=server)

    # Here, we re-use our connection pool
    # not creating a new one
    pool = RedisCache.get_instance()
    return redis.Redis(connection_pool=pool)
