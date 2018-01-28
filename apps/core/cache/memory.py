# coding=utf-8

from apps.core.cache.base import CacheBase, DEFAULT_TIMEOUT
from tornado.concurrent import Future
from tornado import stack_context
from collections import deque
from tornado.ioloop import IOLoop


class LRUCache(dict):
    # TODO:协程安全?

    def __init__(self, maxsize, *args, **kwargs):
        super(LRUCache, self).__init__(*args, **kwargs)
        # 把key保存起来,不用heapq的原因是实际上里面的元素顺序和值无关，
        # 只和调用先后有关,
        self.maxsize = maxsize
        self._lru = deque(self, maxlen=maxsize)

    def get(self, key, default=None):
        if key in self:
            self._refresh(key)
        return dict.get(self, key, default)

    def _refresh(self, key, delete=False):
        """提到最前"""
        self._lru.remove(key)  # O(n)
        if not delete:
            self._lru.append(key)  # O(1)

    def __setitem__(self, key, value):
        # deque达到maxlen之后，会自动挤出左边的数，
        # 但是是静默的,没有同时处理dict本身
        if key not in self:
            if len(self) >= self.maxsize:
                old_key = self._lru.popleft()
                dict.__delitem__(self, old_key)
            self._lru.append(key)
            dict.__setitem__(self, key, value)
        else:
            self._refresh(key)
            dict.__setitem__(self, key, value)

    def __getitem__(self, key):
        value = dict.__getitem__(key)
        # 到这里起码没有异常了
        self._refresh(key)
        return value

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        # 到这里起码没有异常了
        self._refresh(key, delete=True)

    def ttl(self, key):
        """
        >0:还可以存活
        <=0:过期了
        """
        if key in self:
            value, expired = dict.get(self, key)
            return expired - IOLoop.current().time()
        else:
            return -1


class MemoryCache(CacheBase):
    """临时Cache和单元测试Cache实现"""
    DEFAULT_SIZE = 1000

    @classmethod
    def configurable_base(cls):
        return MemoryCache

    def regiest_callback(self, future, callback):
        callback = stack_context.wrap(callback)

        def handle_future(future):
            exc = future.exception()
            if exc is not None:
                response = exc
            else:
                response = future.result()
            self.io_loop.add_callback(callback, response)
        future.add_done_callback(handle_future)

    def get(self, key, default=None, version=None, callback=None):
        future = Future()
        if callback:
            self.regiest_callback(future, callback)
        key = self._make_key(key, version)

        def get_value():
            value = self._cache.get(key)
            if value is not None:
                value, expired = value

                if expired < self.io_loop.time():  # 已过期
                    value = None
                    del self._cache[key]
            future.set_result(value)
        self.io_loop.add_callback(get_value)
        return future

    def get_sync(self, key, default=None, version=None):
        key = self._make_key(key, version)
        value = self._cache.get(key)
        if value is not None:
            value, expired = value

            if expired < self.io_loop.time():  # 已过期
                value = None
                del self._cache[key]
        return value

    def _examin_expired(self, key):  # TODO：加个锁吗。。
        if key in self._cache and self._cache.ttl(key) <= 0:
            del self._cache[key]

    def set(self, key, value,
            timeout=DEFAULT_TIMEOUT, version=None, callback=None):
        future = Future()
        if callback:
            self.regiest_callback(future, callback)
        key = self._make_key(key, version)
        # if timeout
        expired_time = self.get_backend_timeout(timeout)

        def set_value():
            self._cache[key] = (value, expired_time)
            future.set_result(None)
        self.io_loop.add_callback(set_value)
        if expired_time and expired_time > 0:
            self.io_loop.call_at(expired_time,
                                 self._examin_expired,
                                 key)
        return future

    def delete(self, key, version=None, callback=None):
        future = Future()
        if callback:
            self.regiest_callback(future, callback)
        key = self._make_key(key, version)

        def set_value():
            del self._cache[key]
            future.set_result(None)
        self.io_loop.add_callback(set_value)
        return future

    def set_sync(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self._make_key(key, version)
        # if timeout
        expired_time = self.get_backend_timeout(timeout)
        self._cache[key] = (value, expired_time)

    def __contains__(self, key):
        """不附带删除、提到最前的副作用"""
        key = self._make_key(key)
        return self._cache.ttl(key) > 0

    def add(self, key, value,
            timeout=DEFAULT_TIMEOUT, version=None, callback=None):
        pass

    def initialize(self, io_loop, defaults=None):
        max_size = defaults.get(
            'max_size', self.DEFAULT_SIZE) if defaults else self.DEFAULT_SIZE
        self._cache = LRUCache(max_size)
        super(MemoryCache, self).initialize(io_loop, defaults)
