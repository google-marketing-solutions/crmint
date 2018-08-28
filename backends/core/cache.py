from google.appengine.api import memcache

MEMCACHE_DEFAULT_EXPIRATION_TIME_SECONDS = 24 * 60 * 60
MEMCACHE_DEFAULT_MAX_RETRIES = 10

shared_memcache_client = None


def get_memcache_client():
  """Returns a singleton for the memcache client instance."""
  # TODO avoid global variables
  #      implement a memcache client initialized per HTTP incoming request
  global shared_memcache_client
  if shared_memcache_client is not None:
    return shared_memcache_client

  client = memcache.Client()
  shared_memcache_client = client
  return client
