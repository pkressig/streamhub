"""Pre-storage noise filter — rejects URLs that are not real source candidates."""
from __future__ import annotations
import re
from urllib.parse import urlparse

# GitHub pages that are navigation/UI, not indexer instances
_GITHUB_NOISE = re.compile(
    r"github\.com/(search|login|signup|pulls|notifications|marketplace|trending"
    r"|explore|settings|new|organizations|features|about|contact|pricing"
    r"|[^/]+/[^/]+/(issues|pulls|stargazers|watchers|network|forks|releases/latest"
    r"|blob|tree|commits|compare|actions|projects|wiki|security|pulse|graphs|community))",
    re.IGNORECASE,
)

# Social & media platforms — never indexer sources
_SOCIAL_HOSTS = {
    "twitter.com", "x.com", "facebook.com", "instagram.com", "linkedin.com",
    "youtube.com", "tiktok.com", "reddit.com", "discord.com", "discord.gg",
    "t.me", "telegram.org", "whatsapp.com",
}

# CDN / asset hosting — never actual sources
_CDN_HOSTS_RE = re.compile(
    r"(amazonaws\.com|cloudfront\.net|raw\.githubusercontent\.com"
    r"|cdn\.|static\.|assets\.|media\.|img\.|images\.)",
    re.IGNORECASE,
)

# Pure documentation hosting
_DOCS_HOSTS_RE = re.compile(
    r"(gitbook\.io|readthedocs\.(io|org)|docs\.github\.com"
    r"|wiki\.|confluence\.|notion\.so)",
    re.IGNORECASE,
)

# Any github.com URL that is not a potential instance deployment
_GITHUB_REPO_RE = re.compile(r"^github\.com/[^/]+/[^/]+/?$", re.IGNORECASE)


def check(url: str, source_seed: str | None = None) -> tuple[bool, str | None]:
    """
    Returns (passes: bool, rejection_reason: str | None).
    passes=True means the URL may proceed to storage.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "invalid_url"

    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path or "/"

    # Reject bare root paths — no useful content to probe
    if path in ("", "/"):
        return False, "root_path_only"

    # Social platforms
    if host in _SOCIAL_HOSTS:
        return False, "social_link"

    # CDN / raw asset hosts
    if _CDN_HOSTS_RE.search(host):
        return False, "cdn_or_asset_host"

    # Documentation hosting
    if _DOCS_HOSTS_RE.search(host):
        return False, "documentation_host"

    # GitHub noise pages
    if "github.com" in host:
        if _GITHUB_NOISE.search(url):
            return False, "github_noise_page"
        # A bare github.com/owner/repo URL is a repo page, not a source instance
        if _GITHUB_REPO_RE.match(host + path):
            return False, "github_repo_page"
        # github.com URLs without a discernible instance path
        return False, "github_url_not_source"

    return True, None


class NoiseFilter:
    """Stateless filter; use the module-level check() for single calls."""

    def is_noise(self, url: str, source_seed: str | None = None) -> tuple[bool, str | None]:
        passes, reason = check(url, source_seed)
        return (not passes), reason
