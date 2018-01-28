# coding=utf-8

import subprocess
from sqlalchemy.engine.url import make_url
from tornado.options import options


class BaseDatabaseClient(object):

    @classmethod
    def runshell(cls, url, argv):
        args = cls.url_to_cmd_args(url, argv)
        subprocess.call(args)


class SqliteClient(BaseDatabaseClient):
    executable_name = 'sqlite3'

    @classmethod
    def url_to_cmd_args(cls, url, argv=None):
        """sqlite不怎么讲道理啊。。"""
        origin_url = str(url)
        args = [cls.executable_name]
        filename = origin_url.split("://")[1]
        if filename != "/":  # 内存数据库
            args.append(filename)
        print(" ".join(args))
        return args


class MysqlShellClient(BaseDatabaseClient):
    executable_name = 'mysql'

    @classmethod
    def url_to_cmd_args(cls, url, argv=None):
        args = [cls.executable_name]
        args_append = args.append
        args_append("--user=%s" % url.username)

        port = url.port
        if port:
            args_append("--port=%s" % url.port)
        host = url.host
        if host:
            if '/' in host:
                args_append("--socket=%s" % host)
            else:
                args_append("--host=%s" % host)
        query = url.query
        if query and "charset" in query:
            args_append("--default-character-set=%s" % query["charset"])
        args_append(url.database)
        args.extend(argv)
        print(" ".join(args))
        args_append("--password=%s" % url.password)
        return args


class Client(object):
    drivers = {"mysql": MysqlShellClient,
               "sqlite": SqliteClient}

    @classmethod
    def runshell(cls, argv):
        url = make_url(options.db_url)
        drivername = url.drivername
        drivername = drivername.split("+")[0]
        if drivername in cls.drivers:
            client_class = cls.drivers[drivername]
            client_class.runshell(url, argv)
        else:
            print("需要实现对应的数据库客户端驱动:%s" % drivername)
