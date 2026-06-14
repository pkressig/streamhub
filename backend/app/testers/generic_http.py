import httpx
import time
from typing import Optional
from app.testers.base import BaseTester, TestResult

class GenericHttpTester(BaseTester):
    async def test(self, url: str, auth_key: Optional[str] = None) -> TestResult:
        headers = {}
        if auth_key:
            headers["Authorization"] = f"Bearer {auth_key}"
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(url, headers=headers, follow_redirects=True)
            elapsed = int((time.monotonic() - start) * 1000)
            success = response.status_code < 400
            return TestResult(
                success=success,
                response_time_ms=elapsed,
                http_status=response.status_code,
                notes=f"HTTP {response.status_code}",
                tester_type="generic_http",
            )
        except httpx.TimeoutException:
            return TestResult(success=False, notes="Connection timed out", tester_type="generic_http")
        except Exception as e:
            return TestResult(success=False, notes=str(e)[:500], tester_type="generic_http")
