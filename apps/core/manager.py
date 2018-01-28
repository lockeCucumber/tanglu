# coding=utf-8

import sys
import argparse
import apps.conf  # flake8: noqa
from apps.core.models.client import Client
from apps.core.models.reflect import ReflectShell
from apps.core.models import ModelBase
from tornado.options import options
import subprocess
from apps.product.models import (Tag, PreProductTemplate,
                                 Reason,
                                 )
from apps.product.manage.import_category import ImportCategory
from celery.bin.celery import main as celery_main

class BaseManage(object):
    name = None  # 启动子命令
    doc = ""  # 会用这个属性作为子命令文档

    def __init__(self, subparsers):
        self.parser = subparsers.add_parser(self.name, help=self.doc)
        self.add_arguments()
        self.parser.set_defaults(func=self.start)

    def add_arguments(self):
        """写一些启动参数或者不写"""
        pass

    def add_argument(self, *args, **kwargs):
        self.parser.add_argument(*args, **kwargs)

    def start(self, args):
        raise NotImplementedError(
            "manage need implement start func to start command")


class ShellManage(BaseManage):
    name = "shell"
    doc = "ipython shell with tornado env"

    def add_arguments(self):
        """写一些启动参数或者不写"""
        self.add_argument('params', nargs=argparse.REMAINDER,
                          help='other params to ipython')

    def start(self, args):
        from IPython import start_ipython
        sys.exit(start_ipython(args.params))


class DBShellManage(BaseManage):
    name = "dbshell"
    doc = "database shell client"

    def add_arguments(self):
        """写一些启动参数或者不写"""
        self.add_argument('params', nargs=argparse.REMAINDER,
                          help='other params to subprocess')

    def start(self, args):
        Client.runshell(args.params)


class RedisManage(BaseManage):
    name = "redis"
    doc = "start redis-cli"

    def start(self, args):
        args = ['redis-cli']
        redis_options = options.cache_options
        if "host" in redis_options:
            args.append("-h")
            args.append("%s" % redis_options['host'])
        if "port" in redis_options:
            args.append("-p")
            args.append("%s" % redis_options['port'])
        if "selected_db" in redis_options:
            args.append("-n")
            args.append("%s" % redis_options['selected_db'])
        subprocess.call(args)


class ReflectManage(BaseManage):
    name = "reflect"
    doc = "从数据库读取表定义,生成Model class，这样写代码的时候可以有代码补全"

    def add_arguments(self):
        """写一些启动参数或者不写"""
        self.add_argument('table', nargs="+",
                          help='数据库的表名')

    def start(self, args):
        print(args.table)
        for table_name in args.table:
            ReflectShell().start(table_name)


class InitDBManage(BaseManage):
    name = "initdb"
    doc = "创建数据库表"

    def add_arguments(self):
        """写一些启动参数或者不写"""
        self.add_argument('--delete',
                          action="store_true",
                          help='数据库的表名')

    def init_record(self, session):

        tag = Tag(tag_name="测试")
        tag2 = Tag(tag_name="测试2")
        session.add(tag)
        session.add(tag2)
        session.commit()

        ppt = PreProductTemplate(source=0,
                                 cluster_id=1,
                                 category_id=1)
        ppt.restriction_tags.append(tag)
        ppt.restriction_tags.append(tag2)
        ppt.save_object()

        ppt = PreProductTemplate(source=0,
                                 cluster_id=2,
                                 state=PreProductTemplate.STATUS.offline)
        ppt.restriction_tags.append(tag)
        ppt.save_object(session=session)

        r = Reason(text="自动下架", type=Reason.TYPES.machine)
        session.add(r)
        r = Reason(text="手动下架", type=Reason.TYPES.human)
        session.add(r)
        r = Reason(text="不给上架", type=Reason.TYPES.reject)
        session.add(r)
        session.commit()

    def start(self, args):
        session = ModelBase.get_session()
        engine = session.bind
        if args.delete:
            ModelBase.metadata.drop_all(engine)
        ModelBase.metadata.create_all(engine)
        # self.init_record(session)


class CategoryManage(BaseManage, ImportCategory):
    name = "import_category"
    doc = "导入odoo 分类信息"

    def add_arguments(self):
        ImportCategory.add_arguments(self)

    def start(self, args):
        ImportCategory.start(self, args)

class CeleryManage(BaseManage):
    name = "celery"
    doc = "启动celery worker"
    def add_arguments(self):
        self.add_argument("--", dest="no",
                          nargs=1)
        self.add_argument('celery_args',
                          nargs=argparse.REMAINDER,
                          help='Celery启动参数')

    def start(self, args):
        #哎嘿，咋还有个--
        import sys
        print(["celery"] + args.celery_args[1:])
        # sys.setrecursionlimit(200)
        celery_main(["celery"] + args.celery_args[1:])

managers = [ShellManage, DBShellManage,  # flake8: noqa
            RedisManage,
            ReflectManage,
            InitDBManage,
            CategoryManage,
            CeleryManage
            ]
