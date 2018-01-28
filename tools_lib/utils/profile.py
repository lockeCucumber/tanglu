import cProfile
import pstats
import io
from functools import wraps
import io
import logging
logger = logging.getLogger("tornado.application")


class WithProfile(object):
    def __init__(self, debug=False):
        self.debug = debug

    def enter(self):
        self.pr = cProfile.Profile()
        self.pr.enable()

    def __enter__(self):
        if self.debug:
            self.enter()
        return self

    def exit_profile(self):
        self.pr.disable()
        s = io.StringIO()
        sortby = 'tottime'
        ps = pstats.Stats(self.pr, stream=s).sort_stats(
            sortby)
        ps.print_stats(50)
        logger.info(s.getvalue())

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.debug:
            self.exit_profile()
        if exc_type:
            raise exc_val


def setProfile(f):
    @wraps(f)
    def new_f(*args, **kwargs):
        with WithProfile(True):
            return_value = f(*args, **kwargs)
        return return_value
    return new_f
