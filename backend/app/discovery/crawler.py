"""Crawl seed URLs and extract real source candidate URLs (not GitHub pages)."""
from __future__ import annotations
import re
from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl, quote as urlquote
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


async def crawl_reddit(url: str, timeout: float = 20.0) -> list[str]:
    """
    Fetch a Reddit listing as JSON and extract candidate source URLs
    from post titles, bodies, and link targets.
    Never returns github.com/* URLs as candidates.
    """
    candidates: set[str] = set()

    # Convert to Reddit JSON API URL
    parsed = urlparse(url)
    json_path = parsed.path.rstrip("/") + ".json"
    params = dict(parse_qsl(parsed.query))
    params.setdefault("limit", "100")
    params["raw_json"] = "1"
    json_url = urlunparse(parsed._replace(path=json_path, query=urlencode(params)))

    headers = {
        "User-Agent": "PascalHub/0.4 Discovery (open-source research bot)",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, verify=False, headers=headers
        ) as client:
            resp = await client.get(json_url)
            if resp.status_code >= 400:
                return []
            data = resp.json()

        posts: list[dict] = []
        if isinstance(data, dict):
            posts = [c.get("data", {}) for c in data.get("data", {}).get("children", [])]
        elif isinstance(data, list):
            for part in data:
                posts.extend(c.get("data", {}) for c in part.get("data", {}).get("children", []))

        text_to_scan = " ".join(
            (p.get("title", "") or "") + " " +
            (p.get("selftext", "") or "") + " " +
            (p.get("url", "") or "")
            for p in posts
        )

        for m in _INTERESTING_URL_RE.finditer(text_to_scan):
            raw = _clean(m.group(1))
            if raw and not _is_github(raw) and not _skip_ext(raw):
                candidates.add(raw)

        for m in _ANY_URL_RE.finditer(text_to_scan):
            raw = _clean(m.group(0))
            if raw and not _is_github(raw) and not _skip_ext(raw) and "reddit.com" not in raw:
                candidates.add(raw)

        for m in _IP_PORT_RE.finditer(text_to_scan):
            raw = _clean(m.group(0))
            if raw:
                candidates.add(raw)

        base_hosts: set[str] = set()
        for u in list(candidates):
            p = urlparse(u)
            if p.netloc:
                base_hosts.add(f"{p.scheme}://{p.netloc}")
        for base in list(base_hosts)[:15]:
            candidates.add(base + "/api?t=caps")
            candidates.add(base + "/manifest.json")

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


async def crawl_github_user(username: str, timeout: float = 30.0) -> list[str]:
    """Fetch repos owned by a GitHub user/org and extract instance URLs from each."""
    candidates: set[str] = set()
    api_url = f"https://api.github.com/users/{username}/repos?per_page=30&sort=updated&type=owner"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "PascalHub/0.4 Discovery",
    }
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, verify=False, headers=headers) as client:
            resp = await client.get(api_url)
            if resp.status_code >= 400:
                return []
            repos = resp.json()
        for repo in repos[:20]:
            owner = repo.get("owner", {}).get("login", "")
            name = repo.get("name", "")
            if owner and name:
                results = await crawl_github_repo(owner, name, timeout=15.0)
                candidates.update(results)
            homepage = (repo.get("homepage") or "").strip().rstrip("/")
            if homepage and not _is_github(homepage) and homepage.startswith("http"):
                candidates.add(homepage)
    except Exception:
        pass
    return list(candidates)


async def crawl_github_search(query: str, timeout: float = 20.0) -> list[str]:
    """
    Use the GitHub search API to find repositories matching `query`,
    then extract instance URLs from each repo's homepage + README.
    Never returns github.com/* URLs as candidates.
    """
    candidates: set[str] = set()
    api_url = (
        f"https://api.github.com/search/repositories"
        f"?q={urlquote(query)}&per_page=30&sort=updated"
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "PascalHub/0.4 Discovery",
    }

    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, verify=False, headers=headers
        ) as client:
            resp = await client.get(api_url)
            if resp.status_code >= 400:
                return []
            items = resp.json().get("items", [])

        # For each repo: collect homepage + crawl README
        for item in items[:20]:
            homepage = (item.get("homepage") or "").strip().rstrip("/")
            if homepage and not _is_github(homepage) and homepage.startswith("http"):
                candidates.add(homepage)

            owner = item.get("owner", {}).get("login", "")
            repo  = item.get("name", "")
            if owner and repo:
                results = await crawl_github_repo(owner, repo, timeout)
                candidates.update(results)

    except Exception:
        pass

    return list(candidates)
