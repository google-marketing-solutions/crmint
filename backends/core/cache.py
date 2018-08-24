from google.appengine.api import memcache

MEMCACHE_DEFAULT_EXPIRATION_TIME_SECONDS = 24 * 60 * 60
MEMCACHE_DEFAULT_MAX_RETRIES = 10

def get_memcache_client():
  return memcache.Client()

shared_memcache_client = get_memcache_client()

def set_multi_cache(mapping, time=MEMCACHE_DEFAULT_EXPIRATION_TIME_SECONDS, 
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
    cached_mapping = shared_memcache_client.get_multi(mapping, for_cas=True)
    if cached_mapping is None: 
      shared_memcache_client.add_multi(mapping, time=time)
      return True
    if shared_memcache_client.cas_multi(mapping, time=time):
      return True
    retries += 1
  from core.logging import logger
  logger.log_struct({
      'log_level': 'ERROR',
      'message': 'Cannot add to cache mapping: %s' % (mapping),
  })
  return False

def set_cache(key, value, time=MEMCACHE_DEFAULT_EXPIRATION_TIME_SECONDS, 
              max_retries=MEMCACHE_DEFAULT_MAX_RETRIES):
  def handler(val):
    return value
  return set_cache_with_value_function(key, handler, time=time, max_retries=max_retries)

def set_cache_with_value_function(key, value_function, time=MEMCACHE_DEFAULT_EXPIRATION_TIME_SECONDS,
                          max_retries=10):
  retries = 0
  while retries < max_retries:
    cached_value = shared_memcache_client.gets(key)
    if cached_value is None: 
      if shared_memcache_client.add(key, value_function(cached_value), time=time):
        return True
    elif shared_memcache_client.cas(key, value_function(cached_value), time=time):
      return True
    retries += 1
  from core.logging import logger
  logger.log_struct({
      'labels': {
          'key': key,
      },
      'log_level': 'ERROR',
      'message': 'Could not set key "%s" to cache' % (key),
  })
  return False

def get(key, default_value=None, max_retries=10):
  retries = 0
  while retries < max_retries:
    value = shared_memcache_client.gets(key)
    if value is None:
      if default_value:
        # If the key is not initialized in memcache
        # and there is a default_value, 
        # then the cache gets updated with the default_value.
        if shared_memcache_client.add(key, default_value,
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
      'log_level': 'ERROR',
      'message': 'Could not get key "%s" from cache' % (key),
  })
  return False