# coding=utf-8
from __future__ import unicode_literals, absolute_import
from apps.core.models import ModelBase
from typing import Union, Tuple  # 类型注解
from sqlalchemy.orm import Query


class ServiceError(Exception):
    pass


class BaseService(object):
    model_classs = Union[ModelBase]
    REPLACE_ATTR_MAP = {

    }

    @classmethod
    def get_model(cls, pk) -> ModelBase:
        return cls.model_classs.query().get(pk)

    @classmethod
    def list_model(cls, filter_kwargs, query=None, count=True) -> Union[Query, Tuple[Query, int]]:
        model_classs = cls.model_classs
        page = filter_kwargs.pop("page", 1)
        size = filter_kwargs.pop("size", 20)
        offset = (page - 1) * size
        offset = offset if offset > 0 else 0
        if query is None:
            query = model_classs.query()
        for key, value in list(filter_kwargs.items()):
            if key in cls.REPLACE_ATTR_MAP:
                query = query.filter(
                    getattr(model_classs,
                            cls.REPLACE_ATTR_MAP[key]) == value)
            else:
                query = query.filter(getattr(model_classs, key) == value)
        if count:
            total = query.count()
            query = query.limit(size).offset(offset)
            return query, total
        else:
            query = query.limit(size).offset(offset)
            return query
