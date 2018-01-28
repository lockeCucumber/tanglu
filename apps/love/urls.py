#!/usr/bin/env python
# coding:utf-8
from apps.love.views import LoveView
from apps.core.urlutils import urlpattens

routes = [
    (r"/home/", LoveView, None, "love.home"),
]

urls = urlpattens("love", routes)
