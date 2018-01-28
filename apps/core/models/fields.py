# coding=utf-8

from sqlalchemy.types import (TypeDecorator, DateTime,
                              Text, Enum,
                              Date)
from pytz import UTC
from simplejson import loads, dumps
from sqlalchemy.ext.mutable import Mutable
from wtforms.ext.sqlalchemy.orm import ModelConverter, converts
from datetime import datetime, date
from tornado.options import options


class AwareDateTime(TypeDecorator):

    impl = DateTime

    def process_bind_param(self, value, dialect):
        """放入数据库
        原则：如果没有时区信息，那么当做是北京时间,转为UTC后存入数据库
        否则转为UTC后存入数据库
        """
        if value is not None and isinstance(value, datetime):
            if not value.tzinfo:
                value = options.tz.localize(value)
            value = value.astimezone(UTC)

        return value

    def coerce_compared_value(self, op, value):
        """"如果query.filter(Model.field==value)
        的value是date类型，那么使用Date()展开比较的参数
        """
        if isinstance(value, datetime):
            return self
        elif isinstance(value, date):
            return Date().coerce_compared_value(
                op, value)
        else:
            return self

    def process_result_value(self, value, dialect):
        """从数据库取出并变成Python对象,UTC->+8"""
        if value is not None and isinstance(value, datetime):
            if not value.tzinfo:
                value = UTC.localize(value)
            # astimezone有八分钟的平均日出时间
            value = options.tz.normalize(value)
        return value


class CustomerModelConverter(ModelConverter):

    @converts('AwareDateTime')
    def conv_AwareDateTime(self, field_args, **extra):
        return self.conv_DateTime(field_args, **extra)


class MutableList(Mutable, list):
    def __str__(self):
        return dumps(self)

    def __getstate__(self):
        """picker dumps"""
        return list(self)

    def __setstate__(self, state):
        self.extend(state)

    def __setitem__(self, key, value):
        "Detect dictionary set events and emit change events."

        list.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        "Detect dictionary del events and emit change events."

        list.__delitem__(self, key)
        self.changed()

    def __get__(self, instancec, owner):
        list.__get__(self, instancec, owner)
        self.changed()

    def __set__(self, instancec, owner):
        list.__set__(self, instancec, owner)
        self.changed()


class MutableDict(Mutable, dict):

    def __str__(self):
        return dumps(self)

    def __getstate__(self):
        """picker dumps"""
        return dict(self)

    def __setstate__(self, state):
        self.update(state)

    @classmethod
    def coerce(cls, key, value):
        "Convert plain dictionaries to MutableDict."

        if not isinstance(value, MutableDict):
            if isinstance(value, str):
                if value:
                    value = value.strip()
                    value = loads(value)
                else:
                    value = {}
            if isinstance(value, dict):
                return MutableDict(value)
            if isinstance(value, list):
                return MutableList(value)
            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, key, value):
        "Detect dictionary set events and emit change events."

        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        "Detect dictionary del events and emit change events."

        dict.__delitem__(self, key)
        self.changed()


class JSONField(TypeDecorator):
    impl = Text

    def process_bind_param(self, value, dialect):
        """放入数据库"""
        if value is not None:
            if isinstance(value, (dict, list)):
                value = dumps(value)
        else:
            value = dumps({})
        return value

    def process_result_value(self, value, dialect):
        """从数据库取出并变成Python对象,UTC->+8"""
        if value is not None:
            if isinstance(value, str):
                value = loads(value)
        if value is None:
            value = {}
        return value


# 使得对JSONField dict元素的修改，触发session dirty
MutableDict.associate_with(JSONField)


class NoConstraintEnum(Enum):

    def __init__(self, *enums, **kw):
        kw['native_enum'] = False
        super(NoConstraintEnum, self).__init__(*enums, **kw)

    def _should_create_constraint(self, compiler):
        return False


fields = {"AwareDateTime",
          "JSONField",
          "NoConstraintEnum",
          }  # 给alembic用的
