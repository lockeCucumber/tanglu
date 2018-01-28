# coding=utf-8

from apps.core.cache.base import CacheBase, DEFAULT_TIMEOUT
from tornado.gen import Task, coroutine, Return
from pickle import loads, dumps
from tools_lib.redisclient import ReconnectClient
import logging
from tools_lib.utils.encoding import str2bytes, bytes2str
from tornadoredis.connection import ConnectionPool
logger = logging.getLogger("tornado.application")


class RedisCache(CacheBase):

    @classmethod
    def configurable_base(cls):
        return RedisCache

    def initialize(self, io_loop, defaults=None):
        super(RedisCache, self).initialize(io_loop, defaults)
        defaults = self.defaults if defaults is None else defaults
        connect_kwargs = {
            "host": defaults.get("host", "localhost"),
            "port": defaults.get("port", 6379),
            "selected_db": defaults.get("db", 0),
        }
        logger.info("redis cache initialize:%r" % connect_kwargs)
        if "passwd" in defaults:
            connect_kwargs['password'] = defaults['passwd']
        self.passwd = connect_kwargs.pop("password")
        self.selected_db = connect_kwargs.pop("selected_db")
        # 单进程中只用一个连接池，实质用了多个连接
        # 最大连接数由实际并发决定，如果小于实际的并发，会导致一部分请求需要等待
        # 使用更多的连接数，会在高并发的时候占用redis连接，并且实质上也会造成redis压力

        self.pool = ConnectionPool(
            stop_after=10,
            max_connections=200,
            # wait_for_available=True,
            io_loop=io_loop,
            **connect_kwargs)

    def get_request_id(self, client):
        # logger.info("Connection Pool")
        return id(client.connection)

    def __contains__(self, key):
        """不附带删除、提到最前的副作用"""
        key = self._make_key(key)
        return self._sync_cache.ttl(key) > 0

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

        return None if timeout is None else timeout

    async def get(self, key, default=None, version=None, callback=None):
        key = self._make_key(key, version)
        # 从连接池里取一个新的connection
        client = ReconnectClient(
            io_loop=self.io_loop,
            connection_pool=self.pool,
            password=self.passwd,
            selected_db=self.selected_db)
        request_id = self.get_request_id(client)
        logger.info("[%d]redis cache get key:%s", request_id, key)
        result = await Task(client.get, key)
        logger.info("[%d]redis cache get done", request_id)
        if result:
            return loads(str2bytes(result))
        else:
            return result

    @coroutine
    def set(self, key, value,
            timeout=DEFAULT_TIMEOUT, version=None, callback=None):
        key = self._make_key(key, version)
        expired_time = self.get_backend_timeout(timeout)
        value = dumps(value)
        value = bytes2str(value)
        client = ReconnectClient(
            io_loop=self.io_loop,
            connection_pool=self.pool,
            password=self.passwd,
            selected_db=self.selected_db)
        request_id = self.get_request_id(client)
        logger.info("[%d]redis cache set key:%s", request_id, key)
        result = yield Task(client.setex, key, expired_time, value)
        logger.info("[%d]redis cache set done,%s", request_id, type(result))
        raise Return(result)

    async def delete(self, key, version=None):
        key = self._make_key(key, version)
        client = ReconnectClient(
            io_loop=self.io_loop,
            connection_pool=self.pool,
            password=self.passwd,
            selected_db=self.selected_db)
        request_id = self.get_request_id(client)
        logger.info("[%d]redis cache del key:%s", request_id, key)
        result = await Task(client.delete, key)
        logger.info("[%d]redis cache del done", request_id)
        return result

    async def lrange(self, key, start, stop, version=None):
        key = self._make_key(key, version)
        client = ReconnectClient(
            io_loop=self.io_loop,
            connection_pool=self.pool,
            password=self.passwd,
            selected_db=self.selected_db)
        request_id = self.get_request_id(client)
        logger.info("[%d]redis cache lrange key:%s start:%s stop:%s", request_id, key, start, stop)
        result = await Task(client.lrange, key, start, stop)
        logger.info("[%s]redis cache lrange done", request_id)
        return result

    async def llen(self, key, version=None):
        key = self._make_key(key, version)
        client = ReconnectClient(
            io_loop=self.io_loop,
            connection_pool=self.pool,
            password=self.passwd,
            selected_db=self.selected_db)
        request_id = self.get_request_id(client)
        logger.info("[%d]redis cache llen key:%s", request_id, key)
        result = await Task(client.llen, key)
        logger.info("[%d]redis cache llen done", request_id)
        return int(result)

    async def rpush(self, key, data_list, version=None):
        key = self._make_key(key, version)
        client = ReconnectClient(
            io_loop=self.io_loop,
            connection_pool=self.pool,
            password=self.passwd,
            selected_db=self.selected_db)
        request_id = self.get_request_id(client)
        logger.info("[%d]redis cache rpush key:%s", request_id, key)
        result = await Task(client.rpush, key, *data_list)
        logger.info("[%d]redis cache rpush done", request_id)
        return result

    async def expire(self, key, expire, version=None):
        key = self._make_key(key, version)
        client = ReconnectClient(
            io_loop=self.io_loop,
            connection_pool=self.pool,
            password=self.passwd,
            selected_db=self.selected_db)
        request_id = self.get_request_id(client)
        logger.info("[%d]redis key:%s set expire %s", request_id, key, expire)
        result = await Task(client.expire, key, expire)
        logger.info("[%d]redis cache expire one", request_id)
        return result
