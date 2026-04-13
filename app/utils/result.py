class Result:
    """
    统一接口返回格式
    """
    def __init__(self, code=None, msg=None, data=None):
        self.code = code
        self.msg = msg
        self.data = data
    
    @staticmethod
    def success(data=None):
        """
        返回成功结果
        """
        return {
            "code": 200,
            "msg": "success",
            "data": data
        }
    
    @staticmethod
    def error(msg="error", code=0):
        """
        返回错误结果
        """
        return {
            "code": code,
            "msg": msg,
            "data": None
        }
    
    def to_dict(self):
        """
        将对象转换为字典
        """
        return {
            "code": self.code,
            "msg": self.msg,
            "data": self.data
        }