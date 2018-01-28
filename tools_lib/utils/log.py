import logging
from tornado.log import LogFormatter

LOGFORMAT = '%(color)s[%(levelname)1.1s][%(process)d][%(asctime)s.%(msecs)03d %(module)s:%(lineno)d]%(end_color)s %(message)s'


class LogOption(dict):

    def __missing__(self, key):
        return dict.get(self, key)

    def __getattr__(self, key):
        return self.get(key)

    def __setattr__(self, key, value):
        if key in self:
            self[key] = value
        else:
            return super(LogOption, self).__setattr__(key)


def enable_pretty_logging(options=None, logger=None):
    """改进了tornado的日志等级和格式
    """
    if options is None:
        import tornado.options
        options = tornado.options.options
    if options.logging is None or options.logging.lower() == 'none':
        return
    if logger is None:
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, options.logging.upper()))
    if options.log_file_prefix:
        rotate_mode = options.log_rotate_mode
        if rotate_mode == 'size':
            channel = logging.handlers.RotatingFileHandler(
                filename=options.log_file_prefix,
                maxBytes=options.log_file_max_size,
                backupCount=options.log_file_num_backups)
        elif rotate_mode == 'time':
            channel = logging.handlers.TimedRotatingFileHandler(
                filename=options.log_file_prefix,
                when=options.log_rotate_when,
                interval=options.log_rotate_interval,
                backupCount=options.log_file_num_backups)
        else:
            error_message = 'The value of log_rotate_mode option should be ' +\
                            '"size" or "time", not "%s".' % rotate_mode
            raise ValueError(error_message)
        channel.setFormatter(LogFormatter(LOGFORMAT, color=False))
        channel.setLevel(getattr(logging, options.logging.upper()))
        logger.addHandler(channel)
