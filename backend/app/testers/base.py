from dataclasses import dataclass
from typing import Optional
from abc import ABC, abstractmethod

@dataclass
class TestResult:
    success: bool
    response_time_ms: Optional[int] = None
    http_status: Optional[int] = None
    notes: Optional[str] = None
    tester_type: str = "base"

class BaseTester(ABC):
    TIMEOUT = 10.0

    @abstractmethod
    async def test(self, url: str, auth_key: Optional[str] = None) -> TestResult:
        pass
