# coding=utf-8
"""一个SQLAlchemy连接层"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session as SessionBase
# from sqlalchemy.ext.horizontal_shard import ShardedSession
from sqlalchemy.orm.query import Query
from sqlalchemy.util import to_list


class ShardException(Exception):
    pass


class VerticalShardedQuery(Query):
    def __init__(self, entities, session=None):
        super(VerticalShardedQuery, self).__init__(entities,
                                                   session)
        # self.entities = entities
        # 可否在初始化的时候就断言entities所处的shard？

        self.id_chooser = self.session.id_chooser
        self.query_chooser = self.session.query_chooser
        shard_chooser = self.session.shard_chooser

        shards = [shard_chooser(entity.mapper, None)
                  for entity in self._entities]
        if shards:
            first_shard = shards[0]
            all_equals = all(map(lambda x: x == first_shard, shards))
            if not all_equals:
                raise ShardException(
                    "All mapper in query should have the same shard_id:%r" % shards)

        self._shard_id = None

    def set_shard(self, shard_id):
        """return a new query, limited to a single shard ID.

        all subsequent operations with the returned query will
        be against the single shard regardless of other state.
        """
        # entity:ColumnEntity的时候可能为空

        q = self._clone()
        q._shard_id = shard_id
        return q

    def _execute_and_instances(self, context):
        def iter_for_shard(shard_id):
            context.attributes['shard_id'] = shard_id
            result = self._connection_from_session(
                mapper=self._mapper_zero(),
                shard_id=shard_id).execute(
                context.statement,
                self._params)
            return self.instances(result, context)

        if self._shard_id is not None:
            return iter_for_shard(self._shard_id)
        else:
            # 原来的思想是合并query，这里的话应该只要一个吧
            shard_id = self.query_chooser(self)

            # if some kind of in memory 'sorting'
            # were done, this is where it would happen
            return iter_for_shard(shard_id)

    def get(self, ident, **kwargs):
        if self._shard_id is not None:
            return super(VerticalShardedQuery, self).get(ident)
        else:
            ident = to_list(ident)
            for shard_id in self.id_chooser(self, ident):
                o = self.set_shard(shard_id).get(ident, **kwargs)
                if o is not None:
                    return o
            else:
                return None


class VerticalShardedSession(SessionBase):
    """竖直版分片Session，因为SQLAlchemy里的ShardedSession是水平的
    用于一张表的多个db
    这个竖直版用于不同的db里的不同的表,限制:
        一个Session不能跨db查询,抛异常
        同时暂时不支持水平分片支持

    """

    def __init__(self, shard_chooser,
                 id_chooser,
                 query_chooser,
                 shards=None,
                 query_cls=VerticalShardedQuery, **kwargs):

        super(VerticalShardedSession, self).__init__(
            query_cls=query_cls, **kwargs)
        self.shard_chooser = shard_chooser
        self.id_chooser = id_chooser
        self.query_chooser = query_chooser
        self.__binds = {}
        self.shards = shards
        # self.connection_callable = self.connection
        if shards is not None:
            for k in shards:
                self.bind_shard(k, shards[k])

    def connection(self, mapper=None, instance=None, shard_id=None, **kwargs):
        if shard_id is None:
            shard_id = self.shard_chooser(mapper, instance)

        if self.transaction is not None:
            return self.transaction.connection(mapper,
                                               shard_id=shard_id)
        else:
            return self.get_bind(
                mapper,
                shard_id=shard_id,
                instance=instance
            ).contextual_connect(**kwargs)

    def get_bind(self, mapper, shard_id=None,
                 instance=None, clause=None, **kw):
        if shard_id is None:
            shard_id = self.shard_chooser(mapper, instance, clause=clause)
        return self.__binds[shard_id]

    def bind_shard(self, shard_id, bind):
        self.__binds[shard_id] = bind


class Engine(object):
    @classmethod
    def get_engine(cls, db_url, **kwargs):
        engine = create_engine(db_url, **kwargs)
        # engine.connect()
        return engine


# When do I make a sessionmaker?
# Just one time, somewhere in your application’s global scope.
session_factory = sessionmaker(
    expire_on_commit=False,
    class_=VerticalShardedSession
)
Session = scoped_session(session_factory)


def clean_db_session():

    Session.close()
    Session.remove()
