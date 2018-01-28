# coding=utf-8

from tornado.httpclient import HTTPRequest
from tornado.simple_httpclient import SimpleAsyncHTTPClient, _HTTPConnection
from apps.core.datastruct import QueryDict
import base64
import hashlib
import hmac
from datetime import datetime
from functools import partial
from simplejson import dumps
from tools_lib.utils.itercompat import is_iterable
from tools_lib.utils.encoding import ensure_utf8
from http.cookiejar import CookieJar
from tools_lib.cookie import extract_cookies_to_jar, get_cookie_header
from tornado.httputil import HTTPHeaders
import logging
logger = logging.getLogger("tornado.general")
BOUNDARY = 'BoUnDaRyStRiNg'
MULTIPART_CONTENT = 'multipart/form-data; boundary=%s' % BOUNDARY


def genarator_signature(client_secret, string_to_sign):
    """
    http://bugs.python.org/issue5285
    必须确保client_secret是ascii
    """
    client_secret = client_secret.encode("utf-8")
    string_to_sign = string_to_sign.encode("u8")
    signature = base64.encodestring(
        hmac.new(client_secret, string_to_sign, hashlib.sha1).digest())
    return signature[:-1]  # 最后一个\n不要，正好20个字符


def genarator_string(secret, method, path):
    date_string = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    string_to_sign = "{0} {1}\n{2}".format(method,
                                           path,
                                           date_string)
    return genarator_signature(secret, string_to_sign), date_string


def encode_multipart(boundary, data):
    """
    Encodes multipart POST data from a dictionary of form values.

    The key will be used as the form data name; the value will be transmitted
    as content. If the value is a file, the contents of the file will be sent
    as an application/octet-stream; otherwise, str(value) will be sent.
    """
    lines = []
    # Not by any means perfect, but good enough for our purposes.
    # Each bit of the multipart form data could be either a form value or a
    # file, or a *list* of form values and/or files. Remember that HTTP field
    # names can be duplicated!
    for (key, value) in list(data.items()):

        if not isinstance(value, str) and is_iterable(value):
            for item in value:
                # 此处懒，不支持文件了
                # if is_file(item):
                # lines.extend(encode_file(boundary, key, item))
                lines.extend(ensure_utf8(val) for val in [
                    '--%s' % boundary,
                    'Content-Disposition: form-data; name="%s"' % key,
                    '',
                    item
                ])
        else:
            lines.extend(ensure_utf8(val) for val in [
                '--%s' % boundary,
                'Content-Disposition: form-data; name="%s"' % key,
                '',
                value
            ])

    lines.extend([
        ensure_utf8('--%s--' % boundary),
        '',
    ])
    return '\r\n'.join(lines)


class RESTfulAsyncClient(SimpleAsyncHTTPClient):
    """
    沉思：
    Only a single AsyncHTTPClient instance exists per IOLoop
    in order to provide limitations on the number of pending connections.
    ``force_instance=True`` may be used to suppress this behavior.
    """

    def _request_with_params(self, url, method, **kwargs):
        params = kwargs.pop("params", None)
        if params:
            url = url + "?%s" % QueryDict(params).urlencode()
        return self._request(url, method, **kwargs)

    def _request(self, url, method, **kwargs):
        callback = kwargs.pop("callback", None)
        raise_error = kwargs.pop("raise_error", False)
        r = HTTPRequest(url, method, **kwargs)
        logger.info("%s %s %r", method, url, kwargs)

        return self.fetch(r, callback=callback, raise_error=raise_error)

    def get(self, url, params=None, **kwargs):
        return self._request_with_params(url, "GET",
                                         params=params,
                                         **kwargs)

    def post(self, url, data=None, json=False, **kwargs):
        headers = kwargs.pop("headers", {})
        if json:
            """使用JSON发送的POST请求"""
            headers.update({'Content-Type':
                            "application/json; charset=UTF-8",
                            "Accept": "application/json"})
            body = dumps(data)
        else:
            headers.update({'Content-Type':
                            MULTIPART_CONTENT})
            if data:
                body = encode_multipart(BOUNDARY, data)
            else:
                body = ""
        # body = QueryDict(data).urlencode() if data else None
        return self._request_with_params(url, "POST",
                                         body=body,
                                         headers=headers,
                                         **kwargs)

    def put(self, url, data=None, **kwargs):
        body = QueryDict(data).urlencode() if data else None
        headers = kwargs.pop("headers", {})
        headers.update({'Content-Type':
                        'application/x-www-form-urlencoded'})
        return self._request_with_params(url, "PUT",
                                         headers=headers,
                                         body=body,
                                         **kwargs)

    def delete(self, url, data=None, json=False, **kwargs):
        headers = kwargs.pop("headers", {})
        if json:
            """使用JSON发送的POST请求"""
            headers.update({'Content-Type':
                            "application/json; charset=UTF-8",
                            "Accept": "application/json"})
            body = dumps(data)
        else:
            headers.update({'Content-Type':
                            MULTIPART_CONTENT})
            if data:
                body = encode_multipart(BOUNDARY, data)
            else:
                body = ""
        # body = QueryDict(data).urlencode() if data else None
        return self._request_with_params(url, "DELETE",
                                         body=body,
                                         headers=headers,
                                         **kwargs)


class _SessionHTTPConnection(_HTTPConnection):

    def headers_received(self, first_line, headers):
        """重载以提供非标的header_callback"""
        if self.request.expect_100_continue and first_line.code == 100:
            self._write_body(False)
            return
        self.code = first_line.code
        self.reason = first_line.reason
        self.headers = headers

        if self.request.header_callback is not None:
            # 只回调一次
            self.request.header_callback(self.headers, self.request)


class SessionClient(RESTfulAsyncClient):
    """
    实现header_callback
    直接调用fetch不会触发保存 Cookie
    AsyncClient基类控制实现了单例，所以实际上cookiejar也就只有一个
    """

    def initialize(self, *args, **kwargs):
        super(SessionClient, self).initialize(*args, **kwargs)
        # 创建一个cookiejar 整个进程空间，这个实例共享的哈？
        self.cookiejar = CookieJar()

    def _connection_class(self):
        return _SessionHTTPConnection

    def header_callback(self, headers, request):
        """
        借助标准库cookielib和Cookie
        处理响应的Set-Cookie头
        不同的host务必不能串了cookie
        """
        # 把headers里面的cookie提取出来，里面包含cookie的信息
        extract_cookies_to_jar(self.cookiejar, request, headers)

    def _request(self, url, method, **kwargs):
        callback = kwargs.pop("callback", None)
        if "follow_redirects" not in kwargs:
            kwargs['follow_redirects'] = False  # 默认不跟随重定向
        # 不接受外部的header_callback参数，因为已经是非标header_callback了
        kwargs['header_callback'] = self.header_callback
        # 手动添加的cookie不进入self.cookiejar，只会用这一次
        r = HTTPRequest(url, method, **kwargs)
        new_headers = get_cookie_header(self.cookiejar, r)
        old_headers = r.headers
        if isinstance(old_headers, dict):
            r.headers = HTTPHeaders(old_headers)
        if "Cookie" in new_headers:
            r.headers.add("Cookie", new_headers["Cookie"])
        if "Cookie2" in new_headers:  # Cookie2基本啥都没有其实
            r.headers.add("Cookie2", new_headers["Cookie2"])
        return self.fetch(r, callback=callback, raise_error=False)


class BAHTTPClient(object):

    def __init__(self, key, secret, host, ** kwargs):
        self.key = key
        self.secret = secret
        self.host = host
        self.client = RESTfulAsyncClient(**kwargs)

    def handle_request(self, method, path, *args, **kwargs):
        Authorization, Date = genarator_string(
            self.secret, method.upper(), path)
        headers = {"Authorization": "MWS %s:%s" % (self.key, Authorization),
                   "Date": Date}
        if 'headers' in kwargs:
            kwargs['headers'].update(**headers)
        else:
            kwargs['headers'] = headers
        func = getattr(self.client, method)
        return func(self.host + path, *args, **kwargs)

    def __getattr__(self, key):
        if key in {'get', "post", "put", "delete"}:
            return partial(self.handle_request, key)
        return super(BAHTTPClient, self).__getattribute__(key)


class SSOUserClient(object):

    def __init__(self, username, passwd):
        self.client = RESTfulAsyncClient()


class JSONParseClient(object):

    def _parse_json(self, response):
        pass

    def _request(self, url, method, **kwargs):
        callback = kwargs.pop("callback", None)
        if not callback:
            callback = self._parse_json
        r = HTTPRequest(url, method, **kwargs)
        return self.fetch(r, callback=callback)
