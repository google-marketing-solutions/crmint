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


def set_multi_cache(mapping, prefix="",
    time=MEMCACHE_DEFAULT_EXPIRATION_TIME_SECONDS,
    max_retries=MEMCACHE_DEFAULT_MAX_RETRIES):
  """Set multiple values in the cache.

  Arguments:
      mapping: Dictionary of key/value pairs to push into the cache.
      max_retries: Number of times to retry setting values into the cache 
          before raising an exception.
      expiration_time: Integer representing the values expiration time in seconds.
          Defaults to 24 hours
  """
  retries = 0
  while retries < max_retries:
    cached_mapping = get_memcache_client().get_multi(mapping, key_prefix=prefix, for_cas=True)
    if not cached_mapping:
      if get_memcache_client().add_multi(mapping, key_prefix=prefix, time=time):
        return True
    elif get_memcache_client().cas_multi(mapping, key_prefix=prefix, time=time):
      return True
    retries += 1
  from core.logging import logger
  logger.log_struct({
      'log_level': 'WARN',
      'message': 'Could not add to cache mapping: %s' % (mapping),
  })
  return False


def set_cache(key, value, prefix="", time=MEMCACHE_DEFAULT_EXPIRATION_TIME_SECONDS,
    max_retries=MEMCACHE_DEFAULT_MAX_RETRIES):
  mapping = { key: value }
  return set_multi_cache(mapping, prefix=prefix, time=time, max_retries=max_retries)


def set_cache_with_value_function(key, value_function, prefix="",
    time=MEMCACHE_DEFAULT_EXPIRATION_TIME_SECONDS, max_retries=10):
  key = '%s%s' % (prefix, key)
  retries = 0
  while retries < max_retries:
    cached_value = get_memcache_client().gets(key)
    if cached_value is None: 
      if get_memcache_client().add(key, value_function(cached_value), time=time):
        return True
    elif get_memcache_client().cas(key, value_function(cached_value), time=time):
      return True
    retries += 1
  from core.logging import logger
  logger.log_struct({
      'labels': {
          'key': key,
      },
      'log_level': 'WARN',
      'message': 'Could not set key "%s" to cache' % (key),
  })
  return False


def get_or_create(key, default_value=None, prefix="", max_retries=MEMCACHE_DEFAULT_MAX_RETRIES):
  key = '%s%s' % (prefix, key)
  retries = 0
  while retries < max_retries:
    value = get_memcache_client().gets(key)
    if value is None:
      if default_value:
        # If the key is not initialized in memcache
        # and there is a default_value, 
        # then the cache gets updated with the default_value.
        if get_memcache_client().add(key, default_value,
                                    time=MEMCACHE_DEFAULT_EXPIRATION_TIME_SECONDS):
          return default_value
      else:
        return None
    else:
      return value
    retries += 1
  from core.logging import logger
  logger.log_struct({
      'labels': {
          'key': key,
      },
      'log_level': 'WARN',
      'message': 'Could not get key "%s" from cache' % (key),
  })
  return False
