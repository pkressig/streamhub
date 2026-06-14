import httpx
import time
from typing import Optional
from app.testers.base import BaseTester, TestResult


class ManifestTester(BaseTester):
    async def test(self, url: str, auth_key: Optional[str] = None) -> TestResult:
        headers = {}
        if auth_key:
            headers["Authorization"] = f"Bearer {auth_key}"
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(url, headers=headers, follow_redirects=True)
            elapsed = int((time.monotonic() - start) * 1000)
            if response.status_code != 200:
                return TestResult(
                    success=False,
                    response_time_ms=elapsed,
                    http_status=response.status_code,
                    notes=f"HTTP {response.status_code}",
                    tester_type="manifest",
                )
            data = response.json()
            if "id" not in data:
                return TestResult(
                    success=False,
                    response_time_ms=elapsed,
                    http_status=200,
                    notes="No 'id' field in manifest JSON",
                    tester_type="manifest",
                )
            name = data.get("name", "unknown")
            return TestResult(
                success=True,
                response_time_ms=elapsed,
                http_status=200,
                notes=f"Manifest OK: {name}",
                tester_type="manifest",
            )
        except ValueError:
            return TestResult(success=False, notes="Response is not valid JSON", tester_type="manifest")
        except httpx.TimeoutException:
            return TestResult(success=False, notes="Connection timed out", tester_type="manifest")
        except Exception as e:
            return TestResult(success=False, notes=str(e)[:500], tester_type="manifest")
