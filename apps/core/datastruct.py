# coding=utf-8

from collections import defaultdict
from urllib.parse import quote
from urllib.parse import urlencode
from tools_lib.utils.itercompat import is_iterable
from tools_lib.utils.encoding import ensure_utf8


class QueryDict(defaultdict):
    """简化版django.http.QueryDict"""

    def __str__(self):
        return self.urlencode()

    def __init__(self, query_dict):
        super(QueryDict, self).__init__(list)
        for key, value in query_dict.items():
            if not isinstance(value, str):
                if is_iterable(value):
                    self[key] = value
                else:
                    value = "%s" % value
                    self[key].append(value)
            else:
                self[key].append(value)

    def __setitem__(self, key, value):
        value = value if isinstance(value, list) else [value]
        super(QueryDict, self).__setitem__(key, value)

    def urlencode(self, safe=None):
        """
        Returns an encoded string of all query string arguments.

        :arg safe: Used to specify characters which do not require quoting, for
            example::

                >>> q = QueryDict("")
                >>> q['next'] = '/a&b/'
                >>> q.urlencode()
                'next=%2Fa%26b%2F'
                >>> q.urlencode(safe='/')
                'next=/a%26b/'

        """
        output = []
        if safe:
            safe = ensure_utf8(safe)

            def encode(k, v): return '%s=%s' % ((quote(k, safe),
                                                 quote(v, safe)))
        else:
            def encode(k, v): return urlencode({k: v})
        for k, list_ in self.items():
            k = ensure_utf8(k)
            output.extend(encode(k, ensure_utf8(v))
                          for v in list_)
        return '&'.join(output)


# 从Python3里面抄的
try:
    from functools import lru_cache

except ImportError:
    # backport of Python's 3.3 lru_cache, written by Raymond Hettinger and
    # licensed under MIT license, from:
    # <http://code.activestate.com/recipes/578078-py26-and-py30-backport-of-python-33s-lru-cache/>
    # Should be removed when Django only supports Python 3.2 and above.

    from collections import namedtuple
    from functools import update_wrapper
    from threading import RLock

    _CacheInfo = namedtuple(
        "CacheInfo", ["hits", "misses", "maxsize", "currsize"])

    class _HashedSeq(list):
        __slots__ = 'hashvalue'

        def __init__(self, tup, hash=hash):
            self[:] = tup
            self.hashvalue = hash(tup)

        def __hash__(self):
            return self.hashvalue

    def _make_key(args, kwds, typed,
                  kwd_mark=(object(),),
                  fasttypes={int, str, frozenset, type(None)},
                  sorted=sorted, tuple=tuple, type=type, len=len):
        'Make a cache key from optionally typed positional and keyword arguments'
        key = args
        if kwds:
            sorted_items = sorted(kwds.items())
            key += kwd_mark
            for item in sorted_items:
                key += item
        if typed:
            key += tuple(type(v) for v in args)
            if kwds:
                key += tuple(type(v) for k, v in sorted_items)
        elif len(key) == 1 and type(key[0]) in fasttypes:
            return key[0]
        return _HashedSeq(key)

    def lru_cache(maxsize=100, typed=False):
        """Least-recently-used cache decorator.

        If *maxsize* is set to None, the LRU features are disabled and the cache
        can grow without bound.

        If *typed* is True, arguments of different types will be cached separately.
        For example, f(3.0) and f(3) will be treated as distinct calls with
        distinct results.

        Arguments to the cached function must be hashable.

        View the cache statistics named tuple (hits, misses, maxsize, currsize) with
        f.cache_info().  Clear the cache and statistics with f.cache_clear().
        Access the underlying function with f.__wrapped__.

        See:  http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used

        """

        # Users should only access the lru_cache through its public API:
        #       cache_info, cache_clear, and f.__wrapped__
        # The internals of the lru_cache are encapsulated for thread safety and
        # to allow the implementation to change (including a possible C
        # version).

        def decorating_function(user_function):

            cache = dict()
            # make statistics updateable non-locally
            stats = [0, 0]
            HITS, MISSES = 0, 1             # names for the stats fields
            make_key = _make_key
            cache_get = cache.get           # bound method to lookup key or return None
            _len = len                      # localize the global len() function
            lock = RLock()                  # because linkedlist updates aren't threadsafe
            root = []                       # root of the circular doubly linked list
            # initialize by pointing to self
            root[:] = [root, root, None, None]
            # make updateable non-locally
            nonlocal_root = [root]
            PREV, NEXT, KEY, RESULT = 0, 1, 2, 3    # names for the link fields

            if maxsize == 0:

                def wrapper(*args, **kwds):
                    # no caching, just do a statistics update after a
                    # successful call
                    result = user_function(*args, **kwds)
                    stats[MISSES] += 1
                    return result

            elif maxsize is None:

                def wrapper(*args, **kwds):
                    # simple caching without ordering or size limit
                    key = make_key(args, kwds, typed)
                    # root used here as a unique not-found sentinel
                    result = cache_get(key, root)
                    if result is not root:
                        stats[HITS] += 1
                        return result
                    result = user_function(*args, **kwds)
                    cache[key] = result
                    stats[MISSES] += 1
                    return result

            else:

                def wrapper(*args, **kwds):
                    # size limited caching that tracks accesses by recency
                    key = make_key(
                        args, kwds, typed) if kwds or typed else args
                    with lock:
                        link = cache_get(key)
                        if link is not None:
                            # record recent use of the key by moving it to the
                            # front of the list
                            root, = nonlocal_root
                            link_prev, link_next, key, result = link
                            link_prev[NEXT] = link_next
                            link_next[PREV] = link_prev
                            last = root[PREV]
                            last[NEXT] = root[PREV] = link
                            link[PREV] = last
                            link[NEXT] = root
                            stats[HITS] += 1
                            return result
                    result = user_function(*args, **kwds)
                    with lock:
                        root, = nonlocal_root
                        if key in cache:
                            # getting here means that this same key was added to the
                            # cache while the lock was released.  since the link
                            # update is already done, we need only return the
                            # computed result and update the count of misses.
                            pass
                        elif _len(cache) >= maxsize:
                            # use the old root to store the new key and result
                            oldroot = root
                            oldroot[KEY] = key
                            oldroot[RESULT] = result
                            # empty the oldest link and make it the new root
                            root = nonlocal_root[0] = oldroot[NEXT]
                            oldkey = root[KEY]
                            root[KEY] = root[RESULT] = None
                            # now update the cache dictionary for the new links
                            del cache[oldkey]
                            cache[key] = oldroot
                        else:
                            # put result in a new link at the front of the list
                            last = root[PREV]
                            link = [last, root, key, result]
                            last[NEXT] = root[PREV] = cache[key] = link
                        stats[MISSES] += 1
                    return result

            def cache_info():
                """Report cache statistics"""
                with lock:
                    return _CacheInfo(stats[HITS], stats[MISSES], maxsize, len(cache))

            def cache_clear():
                """Clear the cache and cache statistics"""
                with lock:
                    cache.clear()
                    root = nonlocal_root[0]
                    root[:] = [root, root, None, None]
                    stats[:] = [0, 0]

            wrapper.__wrapped__ = user_function
            wrapper.cache_info = cache_info
            wrapper.cache_clear = cache_clear
            return update_wrapper(wrapper, user_function)

        return decorating_function


class MultiDict(dict):

    def getlist(self, name):
        if name in self:
            return [self[name]]
        return []


class AttrDict(dict):
    def __getattr__(self, key):
        return self[key]
