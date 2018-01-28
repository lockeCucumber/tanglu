# coding=utf-8

from tornado.options import options
from motor.motor_tornado import MotorClient


class MongoProxy(object):
    """cache代理
    使用：
    from apps.core.cache import cache
    yield cache.set(key,value,timeout)
    yield cache.get(key)
    yield cache.ttl(key)
    """

    def __init__(self):
        self.engine = None

    def __getattr__(self, attr):
        # 在单元测试的奇妙情况下，不适合用单例，因为ioloop被关闭了
        if self.engine is None:
            self.engine = MotorClient(options.mongo_url)
        return getattr(self.engine, attr)


mongo = MongoProxy()
