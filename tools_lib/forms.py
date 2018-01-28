# coding=utf-8


def unpack_errors(errors):
    return "\n".join(["%s: %s" % (key, value) for key, value in list(errors.items())])
