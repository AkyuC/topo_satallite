import sys


class _const_command(object):
    class const_commandError(TypeError):pass
    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise self.const_commandError("Can't rebind const_command(%s)" % name)
        self.__dict__[name]=value
        
    def __delattr__(self, name):
        if name in self.__dict__:
            raise  self.const_commandError("Can't unbind const_command(%s)" % name)
        raise NameError(name)

# 加载命令常量
sys.modules[__name__] = _const_command()
