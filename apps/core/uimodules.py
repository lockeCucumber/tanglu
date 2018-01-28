# coding=utf-8

from tornado.web import UIModule


class Form(UIModule):

    def render(self, form):
        
        return self.render_string(
            "utils/forms.html", form=form)


class Alert(UIModule):
    """
    level:
        success,info,warning,danger
    """

    def render(self, message, level="success"):
        if message:
            return self.render_string("utils/alert.html",
                                      message=message,
                                      level=level)
        return ""
