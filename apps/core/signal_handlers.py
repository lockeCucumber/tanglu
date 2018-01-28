# coding=utf-8
from __future__ import unicode_literals, absolute_import
from tornado.ioloop import IOLoop
import signal
import logging
from tornado.httpserver import HTTPServer

from functools import partial
logger = logging.getLogger("tornado.application")


def exit_for_loop(server: HTTPServer, signame, *args):
    """退出"""
    logger.warning("Receive:%s signal,exit", signame)
    if server:
        server.stop()
        logger.info("HTTPServer stoped")
    ioloop = IOLoop.current()
    ioloop.stop()
    ioloop.add_callback(ioloop.stop)
    logger.info("IOLoop is close")


SIGNALS = [
    signal.SIGTERM,
    signal.SIGQUIT,
    signal.SIGINT
]


def register_signal_handler(ioloop, server=None):
    """
    supervisord kill时的信号：
    Default: TERM
    有时候用QUIT
    """
    handler = partial(exit_for_loop, server)
    if hasattr(ioloop, "async_ioloop"):
        for s in SIGNALS:
            ioloop.async_ioloop.add_signal_handler(
                s,
                handler
            )
    else:
        for s in SIGNALS:
            signal.signal(s, handler)
