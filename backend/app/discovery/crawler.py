"""Crawl seed URLs and extract real source candidate URLs (not GitHub pages)."""
from __future__ import annotations
import re
from urllib.parse import urlparse
import httpx

# Patterns that indicate actual indexer/source URLs worth probing
_INTERESTING_URL_RE = re.compile(
    r"(https?://[^\s\"'<>]+(?:"
    r"/manifest\.json"
    r"|/torznab(?:/|$)"
    r"|/newznab(?:/|$)"
    r"|/api\?t=caps"
    r"|/api(?:/|$)"
    r"|/feed(?:/|$)"
    r"|/rss(?:/|$)"
    r"))",
    re.IGNORECASE,
)

# Any bare https?:// URL
_ANY_URL_RE = re.compile(r'https?://[^\s"\'<>\]]{10,}', re.IGNORECASE)

_SKIP_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".css", ".js", ".ico", ".svg", ".woff", ".woff2", ".ttf", ".eot", ".map"}

# GitHub README: extract URLs pointing to likely hosted instances (not GitHub itself)
_GITHUB_INSTANCE_URL_RE = re.compile(
    r"(https?://(?!github\.com|raw\.githubusercontent\.com)[^\s\"'<>\]]{8,}"
    r"(?:/manifest\.json|/torznab|/api(?:\?t=caps)?|/feed|/rss)[^\s\"'<>\]]*)",
    re.IGNORECASE,
)

# IP:port patterns (self-hosted instances)
_IP_PORT_RE = re.compile(
    r"https?://(\d{1,3}\.){3}\d{1,3}(:\d{2,5})?(?:/[^\s\"'<>\]]*)?",
    re.IGNORECASE,
)


async def crawl_url(url: str, timeout: float = 15.0) -> list[str]:
    """
    Fetch a URL and extract candidate source URLs.
    Never returns github.com/* URLs as candidates.
    """
    candidates: set[str] = set()
    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, verify=False,
            headers={"User-Agent": "PascalHub/0.4 Discovery"},
        ) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                return []
            text = resp.text

        # Prioritise URLs with known indexer path patterns
        for m in _INTERESTING_URL_RE.finditer(text):
            raw = _clean(m.group(1))
            if raw and not _is_github(raw) and not _skip_ext(raw):
                candidates.add(raw)

        # Also grab IP:port self-hosted patterns
        for m in _IP_PORT_RE.finditer(text):
            raw = _clean(m.group(0))
            if raw:
                candidates.add(raw)

        # For non-GitHub seed pages, also harvest generic URLs (broader net)
        if "github.com" not in url:
            for m in _ANY_URL_RE.finditer(text):
                raw = _clean(m.group(0))
                if raw and not _is_github(raw) and not _skip_ext(raw):
                    candidates.add(raw)

        # Generate /api?t=caps probes for any new base hosts found
        base_hosts: set[str] = set()
        for u in list(candidates):
            p = urlparse(u)
            base_hosts.add(f"{p.scheme}://{p.netloc}")
        for base in list(base_hosts)[:15]:
            candidates.add(base + "/api?t=caps")
            candidates.add(base + "/manifest.json")

    except Exception:
        pass

    return list(candidates)


async def crawl_github_repo(owner: str, repo: str, timeout: float = 15.0) -> list[str]:
    """
    Extract candidate source URLs from a GitHub repo's homepage field and README.
    Never returns any github.com URLs as candidates.
    """
    candidates: set[str] = set()
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "PascalHub/0.4 Discovery",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, verify=False, headers=headers) as client:
            # 1. Repo metadata — homepage field
            r = await client.get(api_url)
            if r.status_code == 200:
                meta = r.json()
                homepage = meta.get("homepage", "") or ""
                if homepage and not _is_github(homepage):
                    candidates.add(homepage.rstrip("/"))

            # 2. README — extract instance URLs
            readme_url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/README.md"
            r2 = await client.get(readme_url)
            if r2.status_code == 200:
                readme = r2.text
                for m in _GITHUB_INSTANCE_URL_RE.finditer(readme):
                    raw = _clean(m.group(1))
                    if raw and not _is_github(raw):
                        candidates.add(raw)
                for m in _IP_PORT_RE.finditer(readme):
                    raw = _clean(m.group(0))
                    if raw and not _is_github(raw):
                        candidates.add(raw)

    except Exception:
        pass

    return list(candidates)


# ── Well-known seed repos to always check ───────────────────────────────────

KNOWN_REPOS: list[tuple[str, str]] = [
    ("iPromKnight", "zilean"),
    ("comet-org", "comet"),
    ("debridmediamanager", "debridmediamanager"),
    ("Stremio", "stremio-web"),
    ("MunifTanjim", "nui"),
]


async def crawl_known_repos(timeout: float = 15.0) -> list[str]:
    """Pull instance URLs from well-known GitHub repos."""
    candidates: list[str] = []
    for owner, repo in KNOWN_REPOS:
        results = await crawl_github_repo(owner, repo, timeout)
        candidates.extend(results)
    return list(set(candidates))


# ── Helpers ──────────────────────────────────────────────────────────────────

def _clean(url: str) -> str:
    return url.rstrip(".,;)'\">#").strip()


def _is_github(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
        return "github.com" in host or "githubusercontent.com" in host
    except Exception:
        return True


def _skip_ext(url: str) -> bool:
    path = urlparse(url).path.lower()
    suffix = path.rsplit(".", 1)[-1] if "." in path else ""
    return f".{suffix}" in _SKIP_EXTENSIONS
