# coding=utf-8

import json
from sqlalchemy.orm.query import Query


class SQLAlchemy2DictEncoder(json.JSONEncoder):

    def __init__(self, **kwargs):
        self.fields = kwargs.pop("fields", None)
        self.fields_callback = kwargs.pop("fields_callback", {})
        super(SQLAlchemy2DictEncoder, self).__init__(**kwargs)

    def encode(self, obj):
        if isinstance(obj, Query):
            query = []
            for o in obj:
                # print type(o)
                query.append(self.encode(o))
            return query
        else:
            # an SQLAlchemy class
            fields = {}
            if self.fields:
                for key in self.fields:
                    if "." in key:
                        index, key = key.split(".")
                        value = getattr(obj[int(index)], key)
                    else:
                        value = getattr(obj, key)
                    if key in self.fields_callback:
                        value = self.fields_callback[key](value)
                    fields[key] = value
                return fields
            for field, data in obj:
                try:
                    # this will fail on non-encodable values, like other
                    # classes
                    json.dumps(data)
                    fields[field] = data
                except TypeError:
                    fields[field] = None
            # a json-encodable dict
            return fields

        # return json.JSONEncoder.encode(self, obj)
