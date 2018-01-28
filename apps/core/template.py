# coding=utf-8

from tornado.template import Loader
import os
from tornado.options import options


class FileLoader(Loader):
    """依旧使用dict缓存模板，只是DEBUG模式下每次判断模板文件的更新时间
    self.templates={
        template_name:(Template,st_mtime),
    }
    """

    def __init__(self, root_directory, **kwargs):
        kwargs["namespace"] = {


        }
        super(FileLoader, self).__init__(root_directory, **kwargs)

    def load(self, name, parent_path=None):
        """Loads a template."""
        name = self.resolve_path(name, parent_path=parent_path)
        with self.lock:
            if options.debug:
                path = os.path.join(self.root, name)
                mtime_now = self._get_file_mtime(path)
                if name in self.templates:
                    template, mtime = self.templates[name]
                    if mtime >= mtime_now:
                        return template
                template = self._create_template(
                    name)
                self.templates[name] = template, mtime_now
                return template
            else:
                if name not in self.templates:
                    self.templates[name] = self._create_template(name)
                return self.templates[name]

    @staticmethod
    def _get_file_mtime(path):
        stat = os.stat(path)
        return stat.st_mtime  # 上次修改时间
