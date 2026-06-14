import httpx
import time
from typing import Optional
from lxml import etree
from app.testers.base import BaseTester, TestResult

class TorznabTester(BaseTester):
    async def test(self, url: str, auth_key: Optional[str] = None) -> TestResult:
        params = {"t": "caps"}
        if auth_key:
            params["apikey"] = auth_key
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                response = await client.get(url, params=params, follow_redirects=True)
            elapsed = int((time.monotonic() - start) * 1000)
            if response.status_code != 200:
                return TestResult(success=False, response_time_ms=elapsed, http_status=response.status_code, notes=f"HTTP {response.status_code}", tester_type="torznab")
            root = etree.fromstring(response.content)
            has_caps = root.tag == "caps" or root.find(".//caps") is not None
            if not has_caps:
                return TestResult(success=False, response_time_ms=elapsed, http_status=200, notes="No <caps> element found in response", tester_type="torznab")
            return TestResult(success=True, response_time_ms=elapsed, http_status=200, notes="Torznab caps endpoint OK", tester_type="torznab")
        except etree.XMLSyntaxError as e:
            return TestResult(success=False, notes=f"Invalid XML: {e}", tester_type="torznab")
        except httpx.TimeoutException:
            return TestResult(success=False, notes="Connection timed out", tester_type="torznab")
        except Exception as e:
            return TestResult(success=False, notes=str(e)[:500], tester_type="torznab")
