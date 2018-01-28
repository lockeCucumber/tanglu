#!/usr/bin/env python
# coding:utf-8

import os
import tornado.web
from tornado.options import define, options, parse_command_line
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

from apps.love.urls import urls as love_urls
from apps.core.template import FileLoader

define("port", default=1314, help="run on the given port", type=int)
define("debug", default=False)

def make_app():
    settings = {
        "debug": options.debug,
        "template_loader": FileLoader("templates/"),
        "static_path": os.path.join(os.path.dirname(__file__), 'static'),
    }
    urls = love_urls
    return tornado.web.Application(urls, **settings)

if __name__ == '__main__':
    parse_command_line()

    app = make_app()
    server = HTTPServer(app)
    server.bind(options.port)
    server.start()

    ioloop = IOLoop.instance()
    ioloop.start()
