"""
Benchmark searchers query sources for specific titles and return result metadata.
Each source type has its own search strategy.
"""
from dataclasses import dataclass, field
from typing import Optional
import time
import httpx
from lxml import etree


@dataclass
class SearchResult:
    success: bool
    result_count: int = 0
    response_time_ms: Optional[int] = None
    duplicate_count: int = 0
    notes: Optional[str] = None


TIMEOUT = 12.0


async def _get(url: str, params: dict, auth_key: Optional[str] = None) -> tuple[Optional[httpx.Response], int, Optional[str]]:
    headers = {}
    if auth_key:
        params = {**params, "apikey": auth_key}
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=headers, follow_redirects=True)
        elapsed = int((time.monotonic() - start) * 1000)
        return resp, elapsed, None
    except httpx.TimeoutException:
        elapsed = int((time.monotonic() - start) * 1000)
        return None, elapsed, "timeout"
    except Exception as e:
        elapsed = int((time.monotonic() - start) * 1000)
        return None, elapsed, str(e)[:200]


def _count_xml_items(content: bytes, tag: str) -> int:
    try:
        root = etree.fromstring(content)
        return len(root.findall(f".//{tag}"))
    except Exception:
        return 0


def _detect_duplicates_xml(content: bytes, title_tag: str) -> int:
    """Count duplicate titles in XML results."""
    try:
        root = etree.fromstring(content)
        titles = [el.text for el in root.findall(f".//{title_tag}") if el.text]
        return len(titles) - len(set(t.lower().strip() for t in titles))
    except Exception:
        return 0


async def search_torznab(url: str, title: str, auth_key: Optional[str] = None) -> SearchResult:
    resp, elapsed, err = await _get(url, {"t": "search", "q": title}, auth_key)
    if err or resp is None:
        return SearchResult(success=False, response_time_ms=elapsed, notes=err or "no response")
    if resp.status_code != 200:
        return SearchResult(success=False, response_time_ms=elapsed, notes=f"HTTP {resp.status_code}")
    count = _count_xml_items(resp.content, "item")
    dups = _detect_duplicates_xml(resp.content, "title") if count > 0 else 0
    return SearchResult(
        success=count > 0,
        result_count=count,
        response_time_ms=elapsed,
        duplicate_count=dups,
        notes=f"{count} results",
    )


async def search_newznab(url: str, title: str, auth_key: Optional[str] = None) -> SearchResult:
    resp, elapsed, err = await _get(url, {"t": "search", "q": title}, auth_key)
    if err or resp is None:
        return SearchResult(success=False, response_time_ms=elapsed, notes=err or "no response")
    if resp.status_code != 200:
        return SearchResult(success=False, response_time_ms=elapsed, notes=f"HTTP {resp.status_code}")
    count = _count_xml_items(resp.content, "item")
    dups = _detect_duplicates_xml(resp.content, "title") if count > 0 else 0
    return SearchResult(
        success=count > 0,
        result_count=count,
        response_time_ms=elapsed,
        duplicate_count=dups,
        notes=f"{count} results",
    )


async def search_rss(url: str, title: str, auth_key: Optional[str] = None) -> SearchResult:
    """RSS feeds can't be queried by title — we fetch and count items as a proxy."""
    resp, elapsed, err = await _get(url, {}, auth_key)
    if err or resp is None:
        return SearchResult(success=False, response_time_ms=elapsed, notes=err or "no response")
    if resp.status_code != 200:
        return SearchResult(success=False, response_time_ms=elapsed, notes=f"HTTP {resp.status_code}")
    count = _count_xml_items(resp.content, "item")
    if count == 0:
        count = _count_xml_items(resp.content, "entry")  # Atom
    return SearchResult(
        success=True,
        result_count=count,
        response_time_ms=elapsed,
        notes=f"RSS feed has {count} items (title search not applicable)",
    )


async def search_generic(url: str, title: str, auth_key: Optional[str] = None) -> SearchResult:
    """Generic HTTP — just check availability, can't search by title."""
    resp, elapsed, err = await _get(url, {}, auth_key)
    if err or resp is None:
        return SearchResult(success=False, response_time_ms=elapsed, notes=err or "no response")
    ok = resp.status_code < 400
    return SearchResult(
        success=ok,
        result_count=0,
        response_time_ms=elapsed,
        notes=f"HTTP {resp.status_code} (title search not applicable)",
    )


SEARCHER_MAP = {
    "torznab": search_torznab,
    "newznab": search_newznab,
    "rss": search_rss,
    "manifest": search_generic,
    "generic_http": search_generic,
}


async def search_source(source_type: str, url: str, title: str, auth_key: Optional[str] = None) -> SearchResult:
    fn = SEARCHER_MAP.get(source_type, search_generic)
    return await fn(url, title, auth_key)
