#!/usr/bin/env python 
# coding:utf-8

from tornado.web import RequestHandler

class LoveView(RequestHandler):

    def get(self):
        self.render('love/home.html')