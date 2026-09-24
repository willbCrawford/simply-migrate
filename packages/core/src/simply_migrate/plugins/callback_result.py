from dataclasses import dataclass, field
from enum import Enum


class CallbackStatus(Enum):
    OK = "ok"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class CallbackResult:
    status: CallbackStatus
    message: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status == CallbackStatus.OK

    @property
    def skip_script(self) -> bool:
        return self.status == CallbackStatus.SKIP

    @classmethod
    def ok(cls, message: str = "", metadata: dict = None) -> "CallbackResult":
        return cls(status=CallbackStatus.OK, message=message, metadata=metadata or {})

    @classmethod
    def fail(cls, message: str = "", metadata: dict = None) -> "CallbackResult":
        return cls(status=CallbackStatus.FAIL, message=message, metadata=metadata or {})

    @classmethod
    def skip(cls, message: str = "", metadata: dict = None) -> "CallbackResult":
        return cls(status=CallbackStatus.SKIP, message=message, metadata=metadata or {})
