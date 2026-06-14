import httpx
import time
from typing import Optional
from lxml import etree
from app.testers.base import BaseTester, TestResult

class RssTester(BaseTester):
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
                return TestResult(success=False, response_time_ms=elapsed, http_status=response.status_code, notes=f"HTTP {response.status_code}", tester_type="rss")
            root = etree.fromstring(response.content)
            tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
            if tag not in ("rss", "feed", "RDF"):
                return TestResult(success=False, response_time_ms=elapsed, http_status=200, notes=f"Unexpected root element: {tag}", tester_type="rss")
            return TestResult(success=True, response_time_ms=elapsed, http_status=200, notes=f"RSS feed OK (root: {tag})", tester_type="rss")
        except etree.XMLSyntaxError as e:
            return TestResult(success=False, notes=f"Invalid XML: {e}", tester_type="rss")
        except httpx.TimeoutException:
            return TestResult(success=False, notes="Connection timed out", tester_type="rss")
        except Exception as e:
            return TestResult(success=False, notes=str(e)[:500], tester_type="rss")
