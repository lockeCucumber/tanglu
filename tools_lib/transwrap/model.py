# coding=utf-8


import logging
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.serializer import loads, dumps
from sqlalchemy.orm import object_mapper
from pytz import UTC
from datetime import datetime
logger = logging.getLogger("sqlalchemy")
BASEOBJ = declarative_base()

UTC_FMT = "%Y-%m-%dT%H:%M:%SZ"


class ModelBaseClass(BASEOBJ):
    """Base class for Nova and Glance Models"""
    __abstract__ = True
    __table_args__ = {'mysql_engine': 'InnoDB',
                      'mysql_charset': 'utf8'}
    __table_initialized__ = False

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def populate_dict(self, d):
        for key, value in list(d.items()):
            self[key] = value

    def __iter__(self):
        # TODO:对sql字段名和ORM属性名不一样的情况需要处理
        self._i = iter(object_mapper(self).columns)
        return self

    def __next__(self):
        n = self._i.next().name
        return n, getattr(self, n)

    def keys(self):
        return [key for key, value in self]

    def dumps(self):
        return dumps(self)

    @classmethod
    def loads(cls, binary_data):
        return loads(binary_data)

    def values(self):
        return [value for key, value in self]

    def items(self):
        return [(key, value) for key, value in self]

    @classmethod
    def get_column_def(cls, colname):
        for c in cls.__table__.columns:
            if c.name == colname:
                return c
        return None

    @classmethod
    def is_column_string(cls, col):
        if hasattr(col.type, 'charset'):
            return True
        else:
            return False

    @staticmethod
    def convert_date2string(at):
        if not at.tzinfo:  # 默认认为是UTC
            at.replace(tzinfo=UTC)
            at_utc = at
        else:  # 否则转换时区
            at_utc = at
        return at_utc.isoformat()

    def to_dict(self, show_time=False):
        ret = {}
        for k, v in self:
            if v is None:
                ret[k] = None
            elif isinstance(v, datetime):
                if not show_time:
                    continue
                v = self.convert_date2string(v)
            elif not isinstance(v, (str, int, float)):
                v = r'%s' % v
            ret[k] = v
        return ret
