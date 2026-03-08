class DemoUserNotFound(Exception):
    def __init__(self, msg=""):
        super().__init__()
        self.msg = msg


class UserNotFound(Exception):
    def __init__(self, msg=""):
        super().__init__()
        self.msg = msg
