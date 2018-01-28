# coding=utf-8

from tornado.web import RequestHandler
from tornado.options import options
from apps.core.models.base import clean_db_session
from tools_lib.utils.profile import WithProfile


class JSONBaseHandler(RequestHandler):
    def initialize(self, *args, **kwargs):
        super(JSONBaseHandler, self).initialize(*args, **kwargs)
        # self.pf = WithProfile(options.debug)
        # self.pf.enter()

    def on_finish(self):
        clean_db_session()
        # self.pf.exit_profile()

    def json_respon(self, json=None, code=200, **kwargs):
        """保证返回的一定是个dict,list会导致信息泄露风险
        RequestHandler.write文档里写得
        """
        if json is not None:
            result = {"data": json, "code": code}
        else:
            result = {"code": code}
        result.update(kwargs)
        self.add_header("Content-Type", "application/json")
        self.write(result)
        self.finish()

    def json_raw(self, data):
        self.add_header("Content-Type", "application/json")
        self.write(data)
        self.finish()

    def json_error_respon(self, json=None, code=400, **kwargs):
        if json is not None:
            result = {"message": json, "code": code}
        else:
            result = {"code": code}
        result.update(kwargs)
        self.add_header("Content-Type", "application/json")
        self.write(result)
        self.set_status(code)
        self.finish()

    def captureException(self, *args, **kwargs):
        if not options.debug:
            super(JSONBaseHandler, self).captureException(*args, **kwargs)
