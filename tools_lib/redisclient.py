# coding=utf-8

from tornadoredis import Client
import logging
logger = logging.getLogger("tornado.application")


class ReconnectClient(Client):
    """重连
    """
    pass
    # connect_kwargs = {}

    # def on_disconnect(self):
    #     """
    #     close时所有已存在的回调函数都会以None被调用：cb(None)
    #     并且置为空
    #     然后才调用该方法
    #     """
    #     # connect_kwargs如果有callback参数会和self.connect的callback冲突
    #     #
    #     logger.warning("redis disconnect,try to connect")
    #     self._io_loop.call_later(1, self.connect,
    #                              )


# class
