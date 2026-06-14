"""Detect what type of indexer/source a URL represents."""
from __future__ import annotations
import re
from urllib.parse import urlparse, urljoin
import httpx

TORZNAB_PATHS = ["/api", "/torznab", "/torznab/api"]
NEWZNAB_PATHS = ["/api", "/newznab", "/newznab/api"]
RSS_CONTENT_TYPES = {"application/rss+xml", "application/atom+xml", "text/xml", "application/xml"}

FAMILY_PATTERNS: list[tuple[str, str]] = [
    (r"torrentio\.strem\.(fun|io)", "torrentio_family"),
    (r"comet\.", "comet_family"),
    (r"mediafusion\.", "mediafusion_family"),
    (r"stremthru\.", "stremthru_family"),
    (r"aiostreams\.", "aiostreams_family"),
    (r"/manifest\.json$", "stremio_manifest"),
    (r"jackett", "jackett"),
    (r"prowlarr", "prowlarr"),
    (r"nzbhydra", "nzbhydra"),
    (r"bitmagnet", "bitmagnet"),
]


async def detect_source_type(url: str, timeout: float = 10.0) -> dict:
    """
    Probe a URL and return:
      {detected_type, name, http_status, response_time_ms, notes, capabilities}
    """
    parsed = urlparse(url)
    result = {
        "detected_type": "unknown",
        "name": parsed.netloc,
        "http_status": None,
        "response_time_ms": None,
        "notes": None,
        "capabilities": {},
    }

    # Pattern-match on URL first (no network needed)
    for pattern, dtype in FAMILY_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            result["detected_type"] = dtype
            break

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, verify=False) as client:
            import time
            t0 = time.monotonic()
            resp = await client.get(url)
            elapsed = (time.monotonic() - t0) * 1000
            result["http_status"] = resp.status_code
            result["response_time_ms"] = round(elapsed, 1)

            content_type = resp.headers.get("content-type", "")
            text = resp.text[:8000]

            # Check for Torznab
            if _is_torznab(text, content_type):
                result["detected_type"] = "torznab"
                caps = _parse_torznab_caps(text)
                result["capabilities"] = caps
                result["name"] = caps.get("title", result["name"])
                return result

            # Check for Newznab
            if _is_newznab(text, content_type):
                result["detected_type"] = "newznab"
                return result

            # Check for RSS/Atom
            if _is_rss(text, content_type):
                result["detected_type"] = "rss"
                result["name"] = _parse_rss_title(text) or result["name"]
                return result

            # Check for Stremio manifest
            if "manifest.json" in url or (resp.status_code == 200 and '"id"' in text and '"version"' in text and '"catalogs"' in text):
                result["detected_type"] = "stremio_manifest"
                try:
                    import json
                    data = json.loads(text)
                    result["name"] = data.get("name", result["name"])
                    result["capabilities"] = {"catalogs": data.get("catalogs", [])[:3]}
                except Exception:
                    pass
                return result

            # Try /api endpoint for torznab/newznab
            if result["detected_type"] == "unknown":
                base = f"{parsed.scheme}://{parsed.netloc}"
                for path in TORZNAB_PATHS:
                    probe_url = base + path + "?t=caps"
                    try:
                        r2 = await client.get(probe_url)
                        if r2.status_code == 200 and _is_torznab(r2.text[:4000], r2.headers.get("content-type", "")):
                            result["detected_type"] = "torznab"
                            caps = _parse_torznab_caps(r2.text)
                            result["capabilities"] = caps
                            result["name"] = caps.get("title", result["name"])
                            return result
                    except Exception:
                        pass

            if resp.status_code < 400:
                if result["detected_type"] == "unknown":
                    result["detected_type"] = "generic_http"

    except httpx.TimeoutException:
        result["notes"] = "timeout"
    except Exception as e:
        result["notes"] = str(e)[:200]

    return result


def _is_torznab(text: str, content_type: str) -> bool:
    return "<caps>" in text or 'xmlns:torznab' in text or ('t=caps' in text and '<category' in text)


def _is_newznab(text: str, content_type: str) -> bool:
    return 'xmlns:newznab' in text or '<newznab:' in text


def _is_rss(text: str, content_type: str) -> bool:
    ct = content_type.lower()
    for rss_ct in RSS_CONTENT_TYPES:
        if rss_ct in ct:
            return True
    return "<rss" in text[:500] or "<feed" in text[:500]


def _parse_torznab_caps(text: str) -> dict:
    caps: dict = {}
    title_match = re.search(r'<title>([^<]+)</title>', text)
    if title_match:
        caps["title"] = title_match.group(1).strip()
    version_match = re.search(r'version="([^"]+)"', text)
    if version_match:
        caps["version"] = version_match.group(1)
    return caps


def _parse_rss_title(text: str) -> str | None:
    m = re.search(r'<title>([^<]+)</title>', text)
    return m.group(1).strip() if m else None
