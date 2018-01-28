# coding=utf-8

from tornado.options import options
from apps.core import timezone
from apps.core.crypto import get_random_string
from datetime import datetime, timedelta


class SessionBase(object):
    """
    Base class for all Session classes.
    """
    TEST_COOKIE_NAME = 'testcookie'
    TEST_COOKIE_VALUE = 'worked'

    def __init__(self, handler, session_key=None):
        self.handler = handler
        self._session_key = session_key
        self.accessed = False
        self.modified = False

    def __contains__(self, key):
        return key in self._session

    def __getitem__(self, key):
        return self._session[key]

    def __setitem__(self, key, value):
        self._session[key] = value
        self.modified = True

    def __delitem__(self, key):
        del self._session[key]
        self.modified = True

    def get(self, key, default=None):
        return self._session.get(key, default)

    def pop(self, key, *args):
        self.modified = self.modified or key in self._session
        return self._session.pop(key, *args)

    def setdefault(self, key, value):
        if key in self._session:
            return self._session[key]
        else:
            self.modified = True
            self._session[key] = value
            return value

    @classmethod
    def new_session_id(self):
        return get_random_string(12)

    def set_test_cookie(self):
        self[self.TEST_COOKIE_NAME] = self.TEST_COOKIE_VALUE

    def test_cookie_worked(self):
        return self.get(self.TEST_COOKIE_NAME) == self.TEST_COOKIE_VALUE

    def delete_test_cookie(self):
        del self[self.TEST_COOKIE_NAME]

    def update(self, dict_):
        self._session.update(dict_)
        self.modified = True

    def has_key(self, key):
        return key in self._session

    def keys(self):
        return list(self._session.keys())

    def values(self):
        return list(self._session.values())

    def items(self):
        return list(self._session.items())

    def iterkeys(self):
        return iter(self._session.keys())

    def itervalues(self):
        return iter(self._session.values())

    def iteritems(self):
        return iter(self._session.items())

    def clear(self):
        # To avoid unnecessary persistent storage accesses, we set up the
        # internals directly (loading data wastes time, since we are going to
        # set it to an empty dict anyway).
        self._session_cache.clear()
        self.accessed = True
        self.modified = True

    def is_empty(self):
        "Returns True when there is no session_key and the session is empty"
        try:
            return not bool(self._session_key) and not self._session_cache
        except AttributeError:
            return True

    def _get_new_session_key(self):
        "Returns session key that isn't being used."
        while True:
            session_key = get_random_string(32)
            if not self.exists(session_key):
                break
        return session_key

    def _get_or_create_session_key(self):
        if self._session_key is None:
            self._session_key = self._get_new_session_key()
        return self._session_key

    def _get_session_key(self):
        return self._session_key

    session_key = property(_get_session_key)

    def _get_session(self, no_load=False):
        """
        Lazily loads session from storage (unless "no_load" is True, when only
        an empty dict is stored) and stores it in the current instance.
        """
        self.accessed = True
        try:
            return self._session_cache
        except AttributeError:
            if self.session_key is None or no_load:
                self._session_cache = {}
            else:
                self._session_cache = self.load()
        return self._session_cache

    _session = property(_get_session)

    def get_expiry_age(self, **kwargs):
        """Get the number of seconds until the session expires.

        Optionally, this function accepts `modification` and `expiry` keyword
        arguments specifying the modification and expiry of the session.
        """
        try:
            modification = kwargs['modification']
        except KeyError:
            modification = timezone.now()
        # Make the difference between "expiry=None passed in kwargs" and
        # "expiry not passed in kwargs", in order to guarantee not to trigger
        # self.load() when expiry is provided.
        try:
            expiry = kwargs['expiry']
        except KeyError:
            expiry = self.get('_session_expiry')

        if not expiry:   # Checks both None and 0 cases
            return options.SESSION_COOKIE_AGE
        if not isinstance(expiry, datetime):
            return expiry
        delta = expiry - modification
        return delta.days * 86400 + delta.seconds

    def get_expiry_date(self, **kwargs):
        """Get session the expiry date (as a datetime object).

        Optionally, this function accepts `modification` and `expiry` keyword
        arguments specifying the modification and expiry of the session.
        """
        try:
            modification = kwargs['modification']
        except KeyError:
            modification = timezone.now()
        # Same comment as in get_expiry_age
        try:
            expiry = kwargs['expiry']
        except KeyError:
            expiry = self.get('_session_expiry')

        if isinstance(expiry, datetime):
            return expiry
        if not expiry:   # Checks both None and 0 cases
            expiry = options.session_cookie_age
        return modification + timedelta(seconds=expiry)

    def set_expiry(self, value):
        """
        Sets a custom expiration for the session. ``value`` can be an integer,
        a Python ``datetime`` or ``timedelta`` object or ``None``.

        If ``value`` is an integer, the session will expire after that many
        seconds of inactivity. If set to ``0`` then the session will expire on
        browser close.

        If ``value`` is a ``datetime`` or ``timedelta`` object, the session
        will expire at that specific future time.

        If ``value`` is ``None``, the session uses the global session expiry
        policy.
        """
        if value is None:
            # Remove any custom expiration for this session.
            try:
                del self['_session_expiry']
            except KeyError:
                pass
            return
        if isinstance(value, timedelta):
            value = timezone.now() + value
        self['_session_expiry'] = value

    def flush(self):
        """
        Removes the current session data from the database and regenerates the
        key.
        """
        self.clear()
        self.delete()
        self._session_key = None

    def cycle_key(self):
        """
        Creates a new session key, whilst retaining the current session data.
        """
        data = self._session_cache
        key = self.session_key
        self.create()
        self._session_cache = data
        self.delete(key)

    # Methods that child classes must implement.

    def exists(self, session_key):
        """
        Returns True if the given session_key already exists.
        """
        raise NotImplementedError(
            'subclasses of SessionBase must provide an exists() method')

    def create(self):
        """
        Creates a new session instance. Guaranteed to create a new object with
        a unique key and will have saved the result once (with empty data)
        before the method returns.
        """
        raise NotImplementedError(
            'subclasses of SessionBase must provide a create() method')

    def save(self):
        """
        Saves the session data. If 'must_create' is True, a new session object
        is created (otherwise a CreateError exception is raised). Otherwise,
        save() can update an existing object with the same key.
        """
        raise NotImplementedError(
            'subclasses of SessionBase must provide a save() method')

    def delete(self, session_key=None):
        """
        Deletes the session data under this key. If the key is None, the
        current session key value is used.
        """
        raise NotImplementedError(
            'subclasses of SessionBase must provide a delete() method')

    def load(self):
        """
        Loads the session data and returns a dictionary.
        """
        raise NotImplementedError(
            'subclasses of SessionBase must provide a load() method')

    @classmethod
    def clear_expired(cls):
        """
        Remove expired sessions from the session store.

        If this operation isn't possible on a given backend, it should raise
        NotImplementedError. If it isn't necessary, because the backend has
        a built-in expiration mechanism, it should be a no-op.
        """
        raise NotImplementedError(
            'This backend does not support clear_expired().')
