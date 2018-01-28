# coding=utf-8
"""
基于SQLAlchemy的Model基类
在此基类中实现数据库连接和一些基础的数据库操作
"""

from tools_lib.transwrap.model import ModelBaseClass
from tools_lib.transwrap.db import (Session, Engine,
                                    clean_db_session, VerticalShardedQuery)

from sqlalchemy.orm import object_mapper, ColumnProperty
from sqlalchemy.ext.declarative import declared_attr
from tornado.options import options
from pytz import UTC
from datetime import datetime
import logging
import enum
from decimal import Decimal
from sqlalchemy.exc import IntegrityError


class WithSession(object):
    session_class = Session

    def __enter__(self):
        self.session = self.session_class()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_t):
        # session.close:
        # Close this Session.
        # This clears all items and ends any transaction in progress.
        # If this session were created with autocommit=False,
        # a new transaction is immediately begun.
        # Note that this new transaction does not use any connection resources
        # until they are first needed.
        if exc_type is not None:
            self.session.rollback()
        self.session.close()


def id_chooser(query: VerticalShardedQuery, ident):
    """
    :param id_chooser: A callable, passed a query and a tuple of identity
          values, which should return a list of shard ids where the ID might
          reside.  The databases will be queried in the order of this listing.
    """
    # mapper = query._mapper_zero()
    return ["default"]


def query_chooser(query: VerticalShardedQuery) -> str:
    """mapper怎么是None呢。。=。=

    似乎在select * 的时候显然就是空的
    """
    mapper = query._mapper_zero()
    if mapper is None:
        return "default"
    _class = mapper.class_
    return getattr(_class, "shard_id", "default")


def shard_chooser(mapper, instance, clause=None):
    if mapper is None:
        return "default"
    _class = mapper.class_
    return getattr(_class, "shard_id", "default")


class ModelBase(ModelBaseClass):
    """Base class for Nova and Glance Models"""
    __abstract__ = True
    __table_args__ = {'mysql_engine': 'InnoDB',
                      'mysql_charset': 'utf8'}
    __table_initialized__ = False
    shards = None
    shard_id = "default" #通过shared_id来判断连接的是何种数据库

    @classmethod
    def get_bind(cls):
        return cls.shards

    @classmethod
    def ensure_bind(cls):
        """此处应该是一个单例，要求Session只运行了一次confifure
        :param shard_chooser: A callable which, passed a Mapper, a mapped
          instance, and possibly a SQL clause, returns a shard ID.  This id
          may be based off of the attributes present within the object, or on
          some round-robin scheme. If the scheme is based on a selection, it
          should set whatever state on the instance to mark it in the future as
          participating in that shard.




        :param shards: A dictionary of string shard names
          to :class:`~sqlalchemy.engine.Engine` objects.


        """
        if not cls.shards:
            cls.shards = {key: Engine.get_engine(db_url,
                                                 **options.db_kwargs)
                          for key, db_url in options.databases.items()}
            Session.configure(shards=cls.shards,
                              query_chooser=query_chooser,
                              id_chooser=id_chooser,
                              shard_chooser=shard_chooser,
                              )

    @classmethod
    def get_session(cls):
        cls.ensure_bind()
        return Session()

    @classmethod
    def with_session(cls):
        cls.ensure_bind()
        return WithSession()

    def save_object(self, session=None, commit=True):
        """Save a new object"""
        if session is None:
            session = ModelBase.get_session()
        session.add(self)
        if commit:
            try:
                session.commit()
            except:
                session.rollback()
                # clean_db_session()
                raise

    def update(self, **kwargs):
        """
        :param kwargs: dict show keys to update
        """
        for k, v in kwargs.items():
            setattr(self, k, v)

    def insert_for_update(self, session=None):
        """实质是根据主键select，然后save"""
        if session is None:
            session = ModelBase.get_session()
        new_instance = session.merge(self)
        session.add(new_instance)
        try:
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            clean_db_session()

    def save_updates(self, session=None):
        """Save a new object"""
        if session is None:
            session = ModelBase.get_session()
        session.add(self)
        try:
            session.commit()
        except:
            session.rollback()
            raise

    def delete(self, session=None):
        if session is None:
            session = ModelBase.get_session()
        session.delete(self)
        try:
            session.commit()
        except:
            session.rollback()
            raise

    def add(self, session=None):
        if session is None:
            session = ModelBase.get_session()
        session.add(self)

    def commit(self, session=None):
        if session is None:
            session = ModelBase.get_session()
        try:
            session.commit()
        except:
            session.rollback()
            raise


    @classmethod
    def query(cls, *args, **kwargs):
        """ Query """
        if "session" in kwargs:
            session = kwargs["session"]
        else:
            session = ModelBase.get_session()
        if len(args) == 0:
            q = session.query(cls)
        else:
            q = session.query(*args)
        return q.set_shard(cls.shard_id)

    @classmethod
    def bulk_insert(cls, mappings, **kwargs):
        """批量插入，需要自行处理插入重复的问题"""
        if "session" in kwargs:
            session = kwargs.pop("session")
        else:
            session = ModelBase.get_session()
        ret = session.bulk_insert_mappings(cls, mappings)
        try:
            session.commit()
        except:
            session.rollback()
            raise
        return ret

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def populate_dict(self, d):
        for key, value in list(d.items()):
            self[key] = value

    def __iter__(self):
        self._i = iter(list(object_mapper(self).attrs.items()))
        # product_id, <ColumnProperty>
        return self

    def __next__(self):
        key, column = next(self._i)
        if isinstance(column, ColumnProperty):
            return key, getattr(self, key)
        else:
            return next(self)

    def keys(self):
        return [key for key, value in self]

    def values(self):
        return [value for key, value in self]

    def items(self):
        return [(key, value) for key, value in self]

    @classmethod
    def create_or_get(cls, **kwargs):
        """
        形如Django create_or_get
        返回obj,is_created
        """
        defaults = kwargs.pop("defaults", {})
        # 判断两个以上有点浪费SQL数量，不写了
        query = cls.query(cls).filter_by(**kwargs)
        obj = query.first()
        if obj:
            return obj, False
        else:
            attr_dict = {}
            attr_dict.update(defaults)
            attr_dict.update(kwargs)
            obj = cls(**attr_dict)
            obj.save_object()
            return obj, True

    @classmethod
    def update_or_create(cls, **kwargs):
        """
        形如Django update_or_create
        kwargs:
            defaults:dict类型，用于更新的字段
            其他字段是用来过滤的
        如果不存在，会创造一个带有kwargs所有字段的对象
        返回obj,is_created
        """
        defaults = kwargs.pop("defaults", {})
        # 判断两个以上有点浪费SQL数量，不写了
        query = cls.query(cls).filter_by(**kwargs)
        obj = query.first()
        if obj:
            for key, value in defaults.items():
                if getattr(obj, key) != value:
                    setattr(obj, key, value)
            session = cls.get_session()
            if obj in session.dirty:  # 如果修改过则保存
                obj.save_object()
            return obj, False
        else:
            attr_dict = {}
            attr_dict.update(defaults)
            attr_dict.update(kwargs)
            obj = cls(**attr_dict)
            obj.save_object()
            return obj, True

    @staticmethod
    def convert_date2string(at):
        if not at.tzinfo:  # 默认认为是UTC
            at.replace(tzinfo=UTC)
            at_utc = at
        else:  # 否则转换时区
            at_utc = at
        return at_utc.isoformat()

    @staticmethod
    def commit(session=None):
        if session is None:
            session = ModelBase.get_session()
        try:
            session.commit()
        except:
            session.rollback()
            raise

    def to_dict(self, show_time=False):
        ret = {}
        for k, v in self:
            if v is None:
                ret[k] = None
            elif isinstance(v, datetime):
                if not show_time:
                    continue
                v = self.convert_date2string(v)
            elif isinstance(v, enum.Enum):
                v = v.name
            elif isinstance(v, Decimal):
                v = float(v)
            elif not isinstance(v, (str, int,
                                    list, dict, float)):
                v = r'%s' % v
            ret[k] = v
        return ret

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

    @declared_attr
    def __tablename__(cls):
        """可以在类定义里面设定__tablename__=xxx或者从这里默认构造出一个表名"""
        class_name = cls.__name__.lower()
        if class_name.endswith("s"):
            return "%s_tbl" % class_name
        else:
            return "%ss_tbl" % class_name


def dump_query(query, show_time=False):
    result = []
    for i in query:
        if isinstance(i, ModelBase):
            result.append(i.to_dict(show_time=show_time))
        elif isinstance(i, list):
            result.append(dump_query(i))
        elif hasattr(i, "_asdict"):  # sqlalchemy.util._collections.result
            # 两个model的tuple也在这里，没想好怎么处理，丢出去吧
            result.append(i._asdict())
        else:
            logging.error("type %s is not implemented" % type(i))
            raise NotImplementedError("type %s is not implemented" % type(i))
    return result
