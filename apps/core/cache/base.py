# coding=utf-8
"""
1. 实现cache
"""

from tornado.util import Configurable
from tornado.ioloop import IOLoop
import weakref
from tornado.util import import_object
from tornado.options import options
from tornado.locks import Lock
DEFAULT_TIMEOUT = object()


def default_key_func(key, key_prefix, version):
    """
    Default function to generate keys.

    Constructs the key used by all other methods. By default it prepends
    the `key_prefix'. KEY_FUNCTION can be used to specify an alternate
    function with custom key making behavior.
    """
    return '%s:%s:%s' % (key_prefix, version, key)


def get_key_func(key_func):
    """
    Function to decide which key function to use.

    Defaults to ``default_key_func``.
    """
    if key_func is not None:
        if callable(key_func):
            return key_func
        else:
            return import_object(key_func)
    return default_key_func


class CacheBase(Configurable):
    """借助Configurable实现单例
    1. 操作应该都是异步的
    >>> def view(self):
    ...     value = yield cache.get(key)
    """
    @classmethod
    def cached_instances(cls):
        attr_name = '_cached_instances_dict_' + cls.__name__
        if not hasattr(cls, attr_name):
            setattr(cls, attr_name, weakref.WeakKeyDictionary())
        return getattr(cls, attr_name)

    def __new__(cls, io_loop=None, force_instance=False, **kwargs):
        io_loop = io_loop or IOLoop.current()
        if force_instance:
            instance_cache = None
        else:
            instance_cache = cls.cached_instances()
        if instance_cache is not None and io_loop in instance_cache:
            return instance_cache[io_loop]
        instance = super(CacheBase, cls).__new__(cls, io_loop=io_loop,
                                                 **kwargs)
        # Make sure the instance knows which cache to remove itself from.
        # It can't simply call _async_clients() because we may be in
        # __new__(AsyncHTTPClient) but instance.__class__ may be
        # SimpleAsyncHTTPClient.
        instance._instance_cache = instance_cache
        if instance_cache is not None:
            instance_cache[instance.io_loop] = instance
        return instance

    def _make_key(self, key, version=None):
        if version is None:
            version = self.version

        new_key = self.key_func(key, self.key_prefix, version)
        return new_key

    def get_backend_timeout(self, timeout=DEFAULT_TIMEOUT):
        """
        Returns the timeout value usable by this backend based upon the provided
        timeout.
        """
        if timeout == DEFAULT_TIMEOUT:
            timeout = self.default_timeout
        elif timeout == 0:
            # ticket 21147 - avoid time.time() related precision issues
            timeout = -1

        return None if timeout is None else self.io_loop.time() + timeout

    def get(self, key, default=None, version=None):
        raise NotImplementedError(
            'subclasses of BaseCache must provide an add() method')

    def get_sync(self, key, default=None, version=None):
        raise NotImplementedError(
            'subclasses of BaseCache must provide an get_sync() method')

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        raise NotImplementedError(
            'subclasses of BaseCache must provide a set() method')

    def set_sync(self, key, default=None, version=None):
        raise NotImplementedError(
            'subclasses of BaseCache must provide a set_sync() method')

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        raise NotImplementedError(
            'subclasses of BaseCache must provide an add() method')

    def initialize(self, io_loop, defaults=None):
        self.io_loop = io_loop
        self.key_func = get_key_func(getattr(options, 'key_func', None))
        self.default_timeout = getattr(options, 'cache_time', 300)
        self.version = getattr(options, 'version', 1)
        self.key_prefix = getattr(options, 'key_prefix', 'cache')
        self.defaults = dict()
        self._lock = Lock()
        if defaults is not None:
            self.defaults.update(defaults)

    def lock(self, timeout=500):
        return self._lock.acquire()

    def release(self):
        return self._lock.release()

    @classmethod
    def configurable_base(cls):
        return CacheBase


class CacheProxy(object):
    """cache代理
    使用：
    from apps.core.cache import cache
    yield cache.set(key,value,timeout)
    yield cache.get(key)
    yield cache.ttl(key)
    """

    def __init__(self):
        self.engine = None

    def initialize(self):
        ioloop = IOLoop.current()
        if self.engine is None or self.engine.io_loop != ioloop:
            CacheBase.configure(options.cache_engine,
                                io_loop=ioloop,
                                )
            self.engine = CacheBase(io_loop=ioloop,
                                    defaults=options.cache_options)
            self.engine.initialize(ioloop, defaults=options.cache_options)

    def __getattr__(self, attr):
        # 在单元测试的奇妙情况下，不适合用单例，因为ioloop被关闭了
        self.initialize()
        return getattr(self.engine, attr)

    def __contains__(self, key):
        self.initialize()
        return key in self.engine


cache = CacheProxy()


def obj2string(obj):
    if isinstance(obj, str):
        return obj
    elif isinstance(obj, int):
        return str(obj)
    elif hasattr(obj, "__name__"):
        return obj.__name__
    else:
        return obj.__class__.__name__


def produce_class_func_cache_key(func, instance, *args, **kwargs):
    cache_key = "%s.%s.%s" % (obj2string(instance),
                              func.__name__,
                              "-".join(map(obj2string, args)))
    if kwargs:
        cache_key += ".".join(["%s=%s" % (key, value)
                               for key, value in kwargs.items()])
    return cache_key


class ModelCache(object):
    def get(self, model_id):
        pass
