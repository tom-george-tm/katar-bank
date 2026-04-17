class APIException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ToolConfigurationException(APIException):
    """Raised when optional tools are misconfigured or fail to load."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message=message, status_code=status_code)
