"""
Source type classifier — runs HTTP probes and returns structured classification.

Returns a ClassificationResult with:
  detected_type, detected_family, confidence (0-100),
  detection_reason, detection_method, name, http_status, response_time_ms, notes
"""
from __future__ import annotations
import json
import re
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

RSS_CONTENT_TYPES = {"application/rss+xml", "application/atom+xml", "text/xml", "application/xml"}

# URL-pattern → (type, family, confidence, reason)
_URL_PATTERNS: list[tuple[re.Pattern, str, str, int, str]] = [
    (re.compile(r"torrentio\.strem\.(fun|io)", re.I), "stremio_manifest", "torrentio_family", 90, "hostname matches Torrentio domain"),
    (re.compile(r"comet\.", re.I), "stremio_manifest", "comet_family", 80, "hostname matches Comet pattern"),
    (re.compile(r"mediafusion\.", re.I), "stremio_manifest", "mediafusion_family", 80, "hostname matches MediaFusion pattern"),
    (re.compile(r"stremthru\.", re.I), "stremio_manifest", "stremthru_family", 80, "hostname matches StremThru pattern"),
    (re.compile(r"aiostreams\.", re.I), "stremio_manifest", "aiostreams_family", 80, "hostname matches AIOStreams pattern"),
    (re.compile(r"/manifest\.json$", re.I), "stremio_manifest", "stremio_manifest", 75, "URL ends in /manifest.json"),
    (re.compile(r"jackett", re.I), "jackett", "jackett", 85, "hostname contains 'jackett'"),
    (re.compile(r"prowlarr", re.I), "prowlarr", "prowlarr", 85, "hostname contains 'prowlarr'"),
    (re.compile(r"nzbhydra", re.I), "nzbhydra", "nzbhydra", 85, "hostname contains 'nzbhydra'"),
    (re.compile(r"bitmagnet", re.I), "bitmagnet", "bitmagnet", 85, "hostname contains 'bitmagnet'"),
    (re.compile(r"/torznab/", re.I), "torznab", "torznab", 80, "URL path contains /torznab/"),
    (re.compile(r"[?&]t=caps", re.I), "torznab", "torznab", 75, "URL contains torznab caps parameter"),
]


@dataclass
class ClassificationResult:
    detected_type: str = "unknown"
    detected_family: str | None = None
    confidence: float = 0.0
    detection_reason: str = "no signals found"
    detection_method: str = "none"
    name: str = ""
    http_status: int | None = None
    response_time_ms: float | None = None
    notes: str | None = None
    capabilities: dict = field(default_factory=dict)


async def classify(url: str, timeout: float = 10.0) -> ClassificationResult:
    """Full classify: URL-pattern match, then HTTP probe with content analysis."""
    parsed = urlparse(url)
    result = ClassificationResult(name=parsed.netloc)

    # Phase 1 — URL pattern matching (free, no network)
    for pattern, dtype, family, conf, reason in _URL_PATTERNS:
        if pattern.search(url):
            result.detected_type = dtype
            result.detected_family = family
            result.confidence = conf
            result.detection_reason = reason
            result.detection_method = "url_pattern"
            break

    # Phase 2 — HTTP probe
    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, verify=False,
            headers={"User-Agent": "PascalHub/0.4 Discovery"},
        ) as client:
            t0 = time.monotonic()
            resp = await client.get(url)
            elapsed = (time.monotonic() - t0) * 1000
            result.http_status = resp.status_code
            result.response_time_ms = round(elapsed, 1)

            if resp.status_code >= 400:
                result.notes = f"HTTP {resp.status_code}"
                return result

            ct = resp.headers.get("content-type", "").lower()
            text = resp.text[:10000]

            # Torznab / Newznab XML
            if _has_torznab(text, ct):
                caps = _parse_xml_caps(text)
                result.detected_type = "torznab"
                result.detected_family = "torznab"
                result.confidence = 95
                result.detection_reason = "response XML contains Torznab namespace or <caps> element"
                result.detection_method = "xml_caps"
                result.name = caps.get("title", result.name)
                result.capabilities = caps
                return result

            if _has_newznab(text, ct):
                result.detected_type = "newznab"
                result.detected_family = "newznab"
                result.confidence = 95
                result.detection_reason = "response XML contains Newznab namespace"
                result.detection_method = "xml_caps"
                return result

            # Stremio manifest JSON
            manifest_hit, manifest_data = _parse_manifest(text, url)
            if manifest_hit:
                family = _manifest_family(url, manifest_data)
                result.detected_type = "stremio_manifest"
                result.detected_family = family
                result.confidence = 92
                result.detection_reason = f"valid Stremio manifest JSON (id={manifest_data.get('id', '?')!r})"
                result.detection_method = "manifest_json"
                result.name = manifest_data.get("name", result.name)
                result.capabilities = {"catalogs": manifest_data.get("catalogs", [])[:3]}
                return result

            # RSS / Atom feed
            if _has_rss(text, ct):
                result.detected_type = "rss"
                result.detected_family = "rss"
                result.confidence = 88
                result.detection_reason = "content-type or opening tag identifies RSS/Atom feed"
                result.detection_method = "html_pattern"
                result.name = _rss_title(text) or result.name
                return result

            # Jackett / Prowlarr / NZBHydra dashboard fingerprints
            fp = _html_fingerprint(text, ct, resp.headers)
            if fp:
                result.detected_type = fp["type"]
                result.detected_family = fp["family"]
                result.confidence = fp["confidence"]
                result.detection_reason = fp["reason"]
                result.detection_method = "html_pattern"
                return result

            # Torznab probe via /api?t=caps on the base URL (if not already known)
            if result.detected_type in ("unknown", "generic_http"):
                base = f"{parsed.scheme}://{parsed.netloc}"
                probe_result = await _probe_torznab(client, base)
                if probe_result:
                    result.detected_type = probe_result["type"]
                    result.detected_family = probe_result["family"]
                    result.confidence = probe_result["confidence"]
                    result.detection_reason = probe_result["reason"]
                    result.detection_method = "xml_caps"
                    result.name = probe_result.get("title", result.name)
                    return result

            # Fallback generic_http — low confidence
            if result.detected_type == "unknown" and resp.status_code < 400:
                result.detected_type = "generic_http"
                result.detected_family = "generic_http"
                result.confidence = 30.0
                result.detection_reason = "reachable HTTP endpoint, no specific type signals found"
                result.detection_method = "html_pattern"

    except httpx.TimeoutException:
        result.notes = "timeout"
    except Exception as e:
        result.notes = str(e)[:200]

    return result


# ── Helpers ─────────────────────────────────────────────────────────────────

def _has_torznab(text: str, ct: str) -> bool:
    return "<caps>" in text or "xmlns:torznab" in text or ("<item" in text and "torznab:" in text)


def _has_newznab(text: str, ct: str) -> bool:
    return "xmlns:newznab" in text or "<newznab:" in text


def _has_rss(text: str, ct: str) -> bool:
    for rct in RSS_CONTENT_TYPES:
        if rct in ct:
            return True
    return "<rss" in text[:500] or "<feed" in text[:500]


def _parse_manifest(text: str, url: str) -> tuple[bool, dict]:
    if "manifest.json" not in url and ('"id"' not in text or '"version"' not in text):
        return False, {}
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "id" in data and "name" in data and "version" in data:
            return True, data
    except Exception:
        pass
    return False, {}


def _manifest_family(url: str, data: dict) -> str:
    name_lower = str(data.get("name", "")).lower()
    desc_lower = str(data.get("description", "")).lower()
    combined = url.lower() + name_lower + desc_lower
    if "torrentio" in combined:
        return "torrentio_family"
    if "comet" in combined:
        return "comet_family"
    if "mediafusion" in combined:
        return "mediafusion_family"
    if "stremthru" in combined:
        return "stremthru_family"
    if "aiostreams" in combined:
        return "aiostreams_family"
    return "stremio_manifest"


def _html_fingerprint(text: str, ct: str, headers) -> dict | None:
    server = headers.get("server", "").lower()
    text_lower = text[:5000].lower()

    checks = [
        ("jackett", ["jackett", "jackett dashboard"], "jackett", 90, "Jackett dashboard fingerprint in page content"),
        ("prowlarr", ["prowlarr", "prowlarr dashboard"], "prowlarr", 90, "Prowlarr dashboard fingerprint in page content"),
        ("nzbhydra", ["nzbhydra", "nzbhydra2"], "nzbhydra", 90, "NZBHydra2 fingerprint in page content"),
        ("bitmagnet", ["bitmagnet", "graphql"], "bitmagnet", 80, "Bitmagnet GraphQL or UI fingerprint"),
    ]
    for family, signals, ftype, conf, reason in checks:
        if any(s in text_lower or s in server for s in signals):
            return {"type": ftype, "family": family, "confidence": conf, "reason": reason}
    return None


async def _probe_torznab(client: httpx.AsyncClient, base_url: str) -> dict | None:
    for path in ["/api?t=caps", "/torznab/api?t=caps"]:
        try:
            r = await client.get(base_url + path, timeout=8.0)
            if r.status_code == 200 and _has_torznab(r.text[:4000], r.headers.get("content-type", "")):
                caps = _parse_xml_caps(r.text)
                return {
                    "type": "torznab", "family": "torznab", "confidence": 93,
                    "reason": f"probe {path} returned valid Torznab caps XML",
                    "title": caps.get("title"),
                }
        except Exception:
            pass
    return None


def _parse_xml_caps(text: str) -> dict:
    caps: dict = {}
    m = re.search(r"<title>([^<]+)</title>", text)
    if m:
        caps["title"] = m.group(1).strip()
    m = re.search(r'version="([^"]+)"', text)
    if m:
        caps["version"] = m.group(1)
    return caps


def _rss_title(text: str) -> str | None:
    m = re.search(r"<title>([^<]+)</title>", text)
    return m.group(1).strip() if m else None
