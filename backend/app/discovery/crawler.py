"""Crawl a seed URL looking for indexer/source URLs."""
from __future__ import annotations
import re
from urllib.parse import urlparse, urljoin
import httpx

# Regex to find bare URLs or href/src attributes
URL_PATTERN = re.compile(
    r'(?:href|src|url)["\s]*[:=]["\s]*'
    r'(https?://[^\s"\'<>]+)'
    r'|'
    r'(https?://[^\s"\'<>]{10,})',
    re.IGNORECASE,
)

INTERESTING_PATHS = ["/api", "/torznab", "/newznab", "/feed", "/rss", "/manifest.json"]
SKIP_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".css", ".js", ".ico", ".svg", ".woff"}


async def crawl_url(url: str, timeout: float = 15.0) -> list[str]:
    """Fetch a URL and extract candidate source URLs from the page."""
    candidates: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, verify=False) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                return candidates
            text = resp.text

        found_urls: set[str] = set()
        for match in URL_PATTERN.finditer(text):
            raw = match.group(1) or match.group(2)
            if not raw:
                continue
            raw = raw.rstrip(".,;)'\"")
            parsed = urlparse(raw)
            if not parsed.netloc:
                continue
            ext = parsed.path.rsplit(".", 1)[-1].lower()
            if f".{ext}" in SKIP_EXTENSIONS:
                continue
            found_urls.add(raw)

        # Also check interesting paths on found base URLs
        base_urls: set[str] = set()
        for u in found_urls:
            p = urlparse(u)
            base_urls.add(f"{p.scheme}://{p.netloc}")

        candidates = list(found_urls)
        for base in list(base_urls)[:20]:
            for path in INTERESTING_PATHS:
                candidates.append(base + path)

    except Exception:
        pass

    return list(set(candidates))


async def crawl_github_search(query: str = "torznab indexer self-hosted", timeout: float = 15.0) -> list[str]:
    """Search GitHub for repos mentioning indexer software and extract URLs."""
    candidates: list[str] = []
    search_url = f"https://github.com/search?q={query.replace(' ', '+')}&type=repositories"
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, verify=False,
                                      headers={"User-Agent": "Mozilla/5.0 PascalHub/0.3"}) as client:
            resp = await client.get(search_url)
            if resp.status_code == 200:
                # Extract repo URLs from search results
                repos = re.findall(r'href="(/[^/"]+/[^/"]+)"', resp.text)
                for repo in repos[:10]:
                    candidates.append(f"https://github.com{repo}")
    except Exception:
        pass
    return candidates
