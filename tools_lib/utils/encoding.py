def ensure_utf8(s):
    """
    unicode to ascii
    u'\\u554a'->'\xe5\x95\x8a'
    """
    if not isinstance(s, str):
        return str(s)
    return s


def str2bytes(s):
    if isinstance(s, str):
        return s.encode("latin")
    return s


def bytes2str(s):
    if isinstance(s, bytes):
        return s.decode("latin")
    return s


def ensure_unicode(s):
    """
    ascii to unicode
    '\xe5\x95\x8a'->u'\\u554a'
    """
    if not isinstance(s, str):
        return str(s)
    if isinstance(s, str):
        return s.decode("u8")
    return s
