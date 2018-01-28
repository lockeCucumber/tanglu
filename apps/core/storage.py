# coding=utf-8

from tornado.options import options
from tools_lib.msslib import MSSClient


class S3Storage(object):

    def __init__(self, bucket, **kwargs):
        self.bucket = bucket
        self.client = MSSClient(**options.MSSCONF)
        # 不新建了吧，万一出错有点危险。。
        # self.client.create_bucket(bucket, **kwargs)

    def save(self, fileobj, name):
        self.client.upload(self.bucket, name, fileobj)

    def delete(self, name):
        self.client.delete(self.bucket, name)

    def get_url(self, name):
        return self.client.get_url(self.bucket, name)

    def clean_all(self):
        bucket = self.client.get_bucket_by_name(self.bucket)
        for obj in bucket.objects.all():
            obj.delete()
