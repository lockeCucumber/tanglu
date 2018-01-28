# coding=utf-8

from apps.core.session.base import SessionBase
from pickle import dumps, loads
from tornado.options import options


class CookieStore(object):

    def __init__(self, handler, _session_key):
        self.handler = handler
        self._session_key = _session_key
        _session_str = self.handler.get_secure_cookie(
            _session_key)
        try:
            self._store = loads(_session_str)
        except:
            self._store = {}

    def __contains__(self, key):
        return key in self._store

    def __getitem__(self, key):
        return self._store.get(key)

    def __setitem__(self, key, value):
        self._store[key] = value

    def __delitem__(self, key):
        del self._store[key]

    def get(self, key, default=None):
        return self._store.get(key, default)

    def pop(self, key, *args):
        return self._store.pop(key, *args)

    def has_key(self, key):
        return key in self._store

    def keys(self):
        return list(self._store.keys())

    def values(self):
        return list(self._store.values())

    def items(self):
        return list(self._store.items())

    def iterkeys(self):
        return iter(self._store.keys())

    def itervalues(self):
        return iter(self._store.values())

    def iteritems(self):
        return iter(self._store.items())

    def clear(self):
        self.handler.clear_cookie(self._session_key)
        return self._store.clear()

    def save(self):
        return self.handler.set_secure_cookie(
            self._session_key,
            dumps(self._store),
            expires_days=options.session_cookie_age,
        )


class CookieSessionStore(SessionBase):

    def load(self):
        """返回一个store"""
        return CookieStore(self.handler, self._session_key)

    def save(self):
        return self._session.save()
