# coding=utf-8
import types


def is_coroutine(obj):
    return obj and isinstance(obj, types.CoroutineType)
