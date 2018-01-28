#!/usr/bin/env python
# coding: utf-8

import re

import arrow
import datetime
from schema import And, Use, Optional, Or
from tornado.escape import utf8, to_unicode
from decimal import Decimal


def power_split(value, separator=',', schema=str):
    assert callable(schema)
    value = utf8(value)
    value = value.strip()
    l = re.split("\s*" + separator + "\s*", value)  # 这个slip直接去除逗号左右的空格
    return [v for v in l if v != '']


schema_utf8_multi = And(Use(utf8), Use(
    lambda x: [_.strip() for _ in x.split(',') if _ != ""]))
schema_unicode_multi = And(Use(utf8), Use(
    lambda x: [to_unicode(_.strip()) for _ in x.split(',') if _ != ""]))
schema_utf8 = And(Use(utf8), len)
schema_utf8_empty = Use(utf8)  # 允许为空的utf8
schema_unicode = And(Use(to_unicode), len, error='请传入不为空的字符串')
schema_unicode_empty = Use(to_unicode, error='请传入合法的字符串')
schema_unicode_upper = And(Use(utf8), len, Use(str.upper), Use(
    lambda x: x.decode(b'utf-8')), error='请传入合法的字符串')
schema_unicode_strip = And(Use(str.strip), schema_unicode)
schema_unicode_title = And(schema_unicode_strip, Use(str.title))
schema_int = Use(int, error='请传入合法的整数')
schema_int_positive = And(Use(int), lambda x: x > 0, error='请传入合法的正整数')
schema_int_non_negtive = And(Use(int), lambda x: x >= 0, error='请传入合法的非负整数')
schema_int_multi = And(Use(utf8), Use(lambda x: [int(_.strip()) for _ in x.split(b',') if _ != ""]),
                       error='请传入以逗号分隔的整数')
schema_float = And(Use(float),
                   Use(lambda x: round(x, 10)), error='')
schema_decimal = And(Use(Decimal))
schema_float_empty = And(Use(lambda x: 0 if x == '' else x), schema_float)
schema_float_2 = And(Use(float), Use(lambda x: round(x, 2)))
# schema_fh_base = And(Use(float), Use(lambda x: round(x, 2)), lambda x: 0 < x < 100)
schema_bool = And(Use(int), Use(bool))
schema_objectid = And(schema_unicode, lambda x: len(x) == 24)
schema_date = And(Use(utf8), Use(arrow.get), Use(lambda x: x.date()))
schema_date_arrow = And(Use(utf8), Use(arrow.get),
                        error='请传入合法的日期, 如:2017-05-20')
schema_datetime = And(Use(utf8), Use(arrow.get), Use(lambda x: x.datetime))
schema_hhmm = And(Use(utf8), Use(lambda x: datetime.time(*list(map(int, x.split(':'))))),
                  Use(lambda x: x.strftime(b"%H:%M")))

email_pattern = re.compile(r'[^@]+@[^@]+\.[^@]+')
schema_email_empty = And(Use(to_unicode), lambda x: email_pattern.search(x))

schema_operator = {
    "id": schema_utf8,
    "name": schema_utf8_empty,
    "tel": schema_utf8,
    "m_type": schema_utf8_empty,
    Optional(object): object
}
schema_receiver = {
    "name": schema_utf8_empty,
    "tel": schema_utf8_empty,
    "addr": schema_utf8_empty,
    "lat": Use(float),
    "lng": Use(float),
    Optional(object): object,
}

schema_operator_unicode = {
    "id": schema_int,
    "name": schema_unicode_empty,
    "tel": schema_unicode,
    # "m_type": schema_unicode_empty,
    Optional(object): object
}
schema_node_x_unicode = {
    'name': schema_unicode_empty,
    'tel': schema_unicode_empty,

    'addr': schema_unicode_empty,
    'lat': schema_float,
    'lng': schema_float,
    'fence': {'id': schema_unicode, 'name': schema_unicode_empty, Optional(object): object},
}
schema_shop_unicode = {
    'id': schema_unicode,
    'name': schema_unicode_empty,
    'tel': schema_unicode,
    'm_type': schema_unicode_empty,

    'lat': schema_float,
    'lng': schema_float,
    Optional('address'): schema_unicode_empty
}
schema_loc = {
    "lat": schema_float,
    "lng": schema_float,
    Optional("addr"): schema_utf8_empty
}

schema_b_specifics = {
    "value": schema_unicode,
    "key": schema_unicode
}

schema_add_sku = {
    "name": schema_unicode,
    Optional("attr_id"): Or(schema_unicode_empty, schema_int)
}

schema_modify_sku = {
    "name": schema_unicode,
    "value_id": schema_int_positive,
    Optional("attr_id"): schema_int_positive
}

schema_update_image = {
    "id": schema_int,
    "url": schema_unicode
}

schema_sku = {
    schema_unicode_title: schema_unicode_title
}

schema_supplier_link = {
    "id": schema_int,
    "url": schema_unicode,
    "active": bool,
    "img": schema_unicode
}

def schema_choice(choices):
    return Or(*choices, error="{} 不是合法的选项")
