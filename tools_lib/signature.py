# coding=utf-8

import base64
import hashlib
import hmac


def genarator_signature(client_secret, string_to_sign):
    """
    http://bugs.python.org/issue5285
    必须确保client_secret是ascii
    """
    client_secret = client_secret.encode("utf-8")
    string_to_sign = string_to_sign.encode("u8")
    signature = base64.encodestring(
        hmac.new(client_secret, string_to_sign, hashlib.sha1).digest())
    return signature[:-1]  # 最后一个\n不要，正好20个字符
