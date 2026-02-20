from typing import Dict

class CallbackResult:
    """Result returned from callback functions"""

    def __init__(self, success: bool = True, message: str = None, data: Dict = None, skip_script: bool = False):
        self.success = success
        self.message = message
        self.data = data or {}
        self.skip_script = skip_script  # If True, skip the current script

    @staticmethod
    def ok(message: str = None, data: Dict = None):
        """Create a successful result"""
        return CallbackResult(success=True, message=message, data=data)

    @staticmethod
    def fail(message: str, data: Dict = None):
        """Create a failed result"""
        return CallbackResult(success=False, message=message, data=data)

    @staticmethod
    def skip(message: str = None):
        """Skip the current script"""
        return CallbackResult(success=True, message=message, skip_script=True)
