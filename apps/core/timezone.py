# coding=utf-8

from tornado.options import options
from tools_lib.utils.time import fmt
from pytz import UTC
from datetime import datetime


def human_readable(at, is_utc=True):
    """打印成本地时区"""
    if not at.tzinfo:
        at = at.replace(tzinfo=UTC)
    at = at.astimezone(options.tz)
    return at.strftime(fmt)


def now():
    at = datetime.now()
    at = at.replace(tzinfo=options.tz)
    return at
