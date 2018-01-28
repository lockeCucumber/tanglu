# coding=utf-8

from datetime import datetime
from pytz import UTC
fmt = '%Y-%m-%d %H:%M:%S'
utc_fmt = "%Y-%m-%dT%H:%M:%SZ"


def get_utcnow():
    at = datetime.utcnow()
    at = at.replace(tzinfo=UTC)
    return at


def isotime(at=None):
    """Stringify time in ISO 8601 format"""
    if not at:
        at = datetime.utcnow()
    if not at.tzinfo:  # 默认认为是UTC
        at.replace(tzinfo=UTC)
        at_utc = at
    else:  # 否则转换时区
        at_utc = at.astimezone(UTC)
    return at_utc.strftime(utc_fmt)
