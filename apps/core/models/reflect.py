# coding=utf-8

from apps.core.models import ModelBase
from sqlalchemy.ext.automap import automap_base

Base = automap_base()


class ReflectShell(object):

    def start(self, table):
        ModelBase.ensure_bind()
        engine = ModelBase.get_bind()
        Base.prepare(engine, reflect=True)
        model_class = getattr(Base.classes, table)
        columns = model_class.__table__.columns
        for column_name, column in list(columns.items()):
            print(column_name, "=", repr(column))
        # pass
