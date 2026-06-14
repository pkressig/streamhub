"""Build a fingerprint hash for a discovered source."""
from __future__ import annotations
import hashlib
import re
from urllib.parse import urlparse


def build_fingerprint(url: str, detected_type: str, capabilities: dict | None = None) -> dict:
    """
    Returns:
      {fingerprint_hash, base_url, api_path, software_family, version_hint, capabilities}
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    api_path = parsed.path or "/"

    software_family = _infer_family(url, detected_type, capabilities or {})
    version_hint = (capabilities or {}).get("version")

    # Hash: base_url + detected_type + software_family (stable across URL variations)
    raw = f"{base_url}|{detected_type}|{software_family or ''}"
    fingerprint_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

    return {
        "fingerprint_hash": fingerprint_hash,
        "base_url": base_url,
        "api_path": api_path,
        "software_family": software_family,
        "version_hint": version_hint,
        "capabilities": capabilities or {},
    }


def _infer_family(url: str, detected_type: str, caps: dict) -> str | None:
    families = {
        "torrentio_family": r"torrentio",
        "comet_family": r"comet",
        "mediafusion_family": r"mediafusion",
        "stremthru_family": r"stremthru",
        "aiostreams_family": r"aiostreams",
        "jackett": r"jackett",
        "prowlarr": r"prowlarr",
        "nzbhydra": r"nzbhydra",
        "bitmagnet": r"bitmagnet",
    }
    for family, pattern in families.items():
        if re.search(pattern, url, re.IGNORECASE):
            return family
    return detected_type if detected_type != "unknown" else None
