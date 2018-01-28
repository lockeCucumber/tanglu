# coding=utf-8

from tornado.testing import AsyncTestCase
from apps.core.models import (ModelBase,)
from tools_lib.transwrap.db import Session
from tornado.options import options
from apps.core.datastruct import QueryDict, lru_cache
from tornado.testing import AsyncHTTPTestCase, gen_test
from apps.core.crypto import get_random_string
from apps.core.cache.base import CacheBase, cache as cache_proxy
from tornado.gen import sleep
from mock import patch
from apps.core.timezone import now
from concurrent.futures import ThreadPoolExecutor
import apps.conf
# 这样不会清掉数据库哈


class EngineTest(AsyncTestCase):
    """overwrite db connect"""
    contexts = None

    def setUp(self):
        if self.contexts is None:
            self.contexts = []
        o = patch.object(options.mockable(), 'databases',
                         {"default": "sqlite:///",
                          "odoo": "sqlite:///",
                          "data_image_match": "sqlite:///",
                          "etl_info": "sqlite:///",
                          "image_match": "sqlite:///",
                          "redshift": "sqlite:///"
                          })
        self.contexts.append(o)
        # 对外请求mock掉，在单元测试里特殊指定响应
        o = patch.object(options.mockable(), 'purchase_url',
                         "http://")
        self.contexts.append(o)
        o = patch.object(options.mockable(), 'odoo_url',
                         "http://")
        self.contexts.append(o)
        for context in self.contexts:
            context.__enter__()
        super(EngineTest, self).setUp()
        session = ModelBase.get_session()
        for key, engine in session.shards.items():
            self.assertEqual(engine.driver, "pysqlite")
            ModelBase.metadata.create_all(engine)

    def tearDown(self):
        session = ModelBase.get_session()
        for engine in session.shards.values():
            self.assertEqual(engine.driver, "pysqlite")
            ModelBase.metadata.drop_all(engine)
        Session.close()
        Session.remove()
        for context in self.contexts:
            context.__exit__()
        super(EngineTest, self).tearDown()

    def test_engine(self):
        engines = ModelBase.get_bind()

        for engine in engines.values():
            self.assertEqual(engine.driver, "pysqlite")
            ModelBase.metadata.create_all(engine)
        # engine = ModelBase.get_bind()
        # self.assertEqual(engine.driver, "pysqlite")


class BaseTestCase(EngineTest):
    contexts = None

    @staticmethod
    def _parse_cookie(cookie_line):
        return cookie_line.split(";")[0]

    def reverse_url(self, url_name, *args):
        return self.get_url(self._app.reverse_url(url_name, *args))


class UrlTestCase(BaseTestCase, AsyncHTTPTestCase):

    def get_app(self):
        import main
        return main.make_app()

    def test_reverse(self):
        self.assertEqual(self._app.reverse_url("user:current"), "/user/")


class DataStructTestCase(EngineTest):

    def test_urlencode_safe(self):
        q = QueryDict({})
        q['next'] = '/a&b/'
        self.assertEqual(q.urlencode(), 'next=%2Fa%26b%2F')
        self.assertEqual(q.urlencode("/"), 'next=/a%26b/')

    def test_urlencode_unicode(self):
        q = QueryDict({})
        q['next'] = '啊'
        self.assertEqual(q.urlencode(), 'next=%E5%95%8A')

    def test_urlencode_list(self):
        q = QueryDict({})
        q['next'] = ['1', "2"]
        self.assertEqual(q.urlencode(), 'next=1&next=2')

    def test_lru(self):
        store = dict(list(zip("abcd", list(range(4)))))

        @lru_cache(2)
        def somefunc(arg):
            return store[arg]

        self.assertEqual(somefunc("a"), 0)
        self.assertEqual(somefunc("b"), 1)
        cache_info = somefunc.cache_info()
        self.assertEqual(cache_info.misses, 2)
        self.assertEqual(cache_info.hits, 0)

        self.assertEqual(somefunc("a"), 0)
        self.assertEqual(somefunc("b"), 1)

        cache_info = somefunc.cache_info()
        self.assertEqual(cache_info.misses, 2)
        self.assertEqual(cache_info.hits, 2)

        somefunc.cache_clear()
        self.assertEqual(somefunc("a"), 0)
        self.assertEqual(somefunc("b"), 1)
        cache_info = somefunc.cache_info()
        self.assertEqual(cache_info.misses, 2)
        self.assertEqual(cache_info.hits, 0)

        self.assertEqual(somefunc("c"), 2)
        self.assertEqual(somefunc("d"), 3)
        cache_info = somefunc.cache_info()
        self.assertEqual(cache_info.misses, 4)
        self.assertEqual(cache_info.hits, 0)

    def test_lru_nosize(self):
        store = dict(list(zip("abcd", list(range(4)))))

        @lru_cache(None)
        def somefunc(arg):
            return store[arg]
        self.assertEqual(somefunc("a"), 0)
        self.assertEqual(somefunc("b"), 1)
        cache_info = somefunc.cache_info()
        self.assertEqual(cache_info.misses, 2)
        self.assertEqual(cache_info.hits, 0)


class TestCrypto(EngineTest):

    def test_random(self):
        self.assertEqual(len(get_random_string(12)), 12)
        self.assertEqual(len(get_random_string(20)), 20)
        self.assertNotEqual(get_random_string(12), get_random_string(12))


class TestTimeUtils(EngineTest):

    def test_now(self):
        dt = now()
        self.assertIsNotNone(dt.tzinfo)


class MemoryCacheTestCase(EngineTest):
    contexts = None

    def setUp(self):
        if self.contexts is None:
            self.contexts = []
        o = patch.object(options.mockable(), 'cache_engine',
                         "apps.core.cache.memory.MemoryCache")
        self.contexts.append(o)
        super(MemoryCacheTestCase, self).setUp()

    @gen_test
    def test_get(self):
        CacheBase.configure(
            "apps.core.cache.memory.MemoryCache", io_loop=self.io_loop)
        cache = CacheBase(self.io_loop)
        value = yield cache.get("key_not_exist")
        self.assertEqual(value, None)

    @gen_test
    def test_set(self):
        CacheBase.configure(
            "apps.core.cache.memory.MemoryCache", io_loop=self.io_loop)
        cache = CacheBase(self.io_loop)
        yield cache.set("somekey", 1)
        value = yield cache.get("somekey")
        self.assertEqual(value, 1)

    @gen_test
    def test_size_set(self):
        CacheBase.configure(
            "apps.core.cache.memory.MemoryCache", io_loop=self.io_loop,
            defaults={"max_size": 2})
        cache = CacheBase()
        yield cache.set("somekey", 1)
        yield cache.set("somekey2", 2)
        yield cache.set("somekey3", 3)
        value = yield cache.get("somekey")
        self.assertEqual(value, None)

    @gen_test
    def test_size_lru(self):
        CacheBase.configure(
            "apps.core.cache.memory.MemoryCache", io_loop=self.io_loop,
            defaults={"max_size": 2})
        cache = CacheBase()
        yield cache.set("somekey", 1)
        yield cache.set("somekey2", 2)
        # yield cache.set("somekey3", 3)

        value = yield cache.get("somekey")
        self.assertEqual(value, 1)

        yield cache.set("somekey3", 3)  # somekey2被挤出

        value = yield cache.get("somekey")
        self.assertEqual(value, 1)

        value = yield cache.get("somekey2")
        self.assertEqual(value, None)

    @gen_test
    def test_timeout(self):
        CacheBase.configure(
            "apps.core.cache.memory.MemoryCache", io_loop=self.io_loop,
            defaults={"max_size": 2})
        cache = CacheBase()
        yield cache.set("somekey", 1, 1)
        yield cache.set("somekey2", 2, 2)
        yield sleep(2)

        self.assertNotIn("somekey", cache._cache)
        self.assertNotIn("somekey", cache)

    @gen_test
    def test_proxy(self):
        o = patch.object(options.mockable(),
                         'cache_options',
                         {"max_size": 2})
        o.__enter__()
        self.contexts.append(o)
        o = patch.object(options.mockable(),
                         'cache_engine',
                         "apps.core.cache.memory.MemoryCache")
        o.__enter__()
        self.contexts.append(o)
        yield cache_proxy.set("somekey", 1, 1)
        yield cache_proxy.set("somekey2", 2, 2)
        yield sleep(2)
        self.assertNotIn("somekey", cache_proxy._cache)
        self.assertNotIn("somekey", cache_proxy)


class A(object):
    def __init__(self, i):
        self.i = i


class RedisCacheTest(BaseTestCase):
    # teardown怎么清掉呢。。。。

    @gen_test
    def test_get(self):
        CacheBase.configure("apps.core.cache.redis.RedisCache",
                            defaults=options.cache_options)
        cache = CacheBase(self.io_loop)
        # 等auth和select完成
        yield sleep(0.1)
        value = yield cache.get("key_not_exist")
        self.assertEqual(value, None)

    @gen_test
    def test_set(self):
        CacheBase.configure("apps.core.cache.redis.RedisCache",
                            defaults=options.cache_options)
        cache = CacheBase(self.io_loop)
        yield sleep(0.1)
        yield cache.set("testkey", "value")
        value = yield cache.get("testkey",)
        self.assertEqual(value, "value")
        yield cache.delete("testkey")
        value = yield cache.get("testkey",)
        self.assertEqual(value, None)

    @gen_test
    def test_set_object(self):
        CacheBase.configure("apps.core.cache.redis.RedisCache",
                            defaults=options.cache_options)
        cache = CacheBase(self.io_loop)
        yield sleep(0.1)

        obj = A(123123)
        yield cache.set("testkey", obj)
        value = yield cache.get("testkey",)
        self.assertEqual(isinstance(value, A), True)
        self.assertEqual(value.i, 123123)
        yield cache.delete("testkey")
        value = yield cache.get("testkey",)
        self.assertEqual(value, None)

    @gen_test
    def test_set_dict(self):
        CacheBase.configure("apps.core.cache.redis.RedisCache",
                            defaults=options.cache_options)
        cache = CacheBase(self.io_loop)
        yield sleep(0.1)

        obj = {"asd": 123, "zxc": "qwe"}
        yield cache.set("testkey", obj)
        value = yield cache.get("testkey",)
        self.assertEqual(isinstance(value, dict), True)
        self.assertDictEqual(value, {"asd": 123, "zxc": "qwe"})
        yield cache.delete("testkey")
        value = yield cache.get("testkey",)
        self.assertEqual(value, None)

    @gen_test
    def test_bin(self):
        CacheBase.configure("apps.core.cache.redis.RedisCache",
                            defaults=options.cache_options)
        cache = CacheBase(self.io_loop)

        yield sleep(0.1)
        obj = {"asd": 123, "zxc": "啊"}
        yield cache.set("testkey", obj)

        value = yield cache.get("testkey",)
        self.assertDictEqual(value, {"asd": 123, "zxc": "啊"})
        self.assertTrue(isinstance(value["zxc"], str))

        obj = {"asd": 123, "zxc": b"\x00\x01\x02"}
        yield cache.set("testkey2", obj)

        value = yield cache.get("testkey2",)
        self.assertTrue(isinstance(value["zxc"], bytes))
        self.assertEqual(value["zxc"], b"\x00\x01\x02")
