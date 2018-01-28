# coding=utf-8

from tornado.web import URLSpec


class urlpattens(object):
    """
    提供形如Django的树形url结构
    urls = urlpattens('user',
        [
            ("/login/,LoginHandler),
            ("/callback,CallbackHandler),
        ]
    )
    TODO:只有一层的节点
    """

    def new_urlSpec(self, pattern, handler, kwargs=None, name=None):
        if name:
            name = "%s:%s" % (self.name, name)
        return URLSpec('%s%s' % (self.prefix, pattern),
                       handler,
                       kwargs=kwargs,
                       name=name
                       )

    def __init__(self, name, urlhandlers, prefix=None):
        self.name = name
        if prefix:
            self.prefix = prefix
        else:
            self.prefix = "/%s" % name if name else ''
        self.urlhandlers = []
        for handler_args in urlhandlers:
            self.urlhandlers.append(
                self.new_urlSpec(*handler_args)
            )

    def __add__(self, other_urls):
        """
        self+other_urls
        """
        if isinstance(other_urls, list):  # 和列表相加后得到一个新的list
            return self.urlhandlers + other_urls
        elif isinstance(other_urls, urlpattens):
            return self.urlhandlers + other_urls.urlhandlers

    def __radd__(self, other_urls):
        """
        other_urls+self
        """
        if isinstance(other_urls, list):  # 和列表相加后得到一个新的list
            return other_urls + self.urlhandlers
        elif isinstance(other_urls, urlpattens):
            return other_urls.urlhandlers + self.urlhandlers

    def __iter__(self):
        return iter(self.urlhandlers)

    @property
    def urls(self):
        return self.urlhandlers
