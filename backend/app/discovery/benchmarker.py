"""
Real content benchmarker for DiscoveredSource objects.
Tests stremio stream endpoints and torznab/newznab search APIs with
hardcoded IMDb IDs. Scans result titles/filenames for language markers.
"""
from __future__ import annotations
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx
from lxml import etree

# ── Language / quality detection patterns ────────────────────────────────────

_ITA_RE = re.compile(
    r'\b(ITA|ita|italiano|ITALIANO|ITALICO)\b|[\[(_.]ITA[\])_.]|[\[(_.]IT[\])_.]',
    re.IGNORECASE,
)
_GER_RE = re.compile(
    r'\b(GER|ger|deutsch|DEUTSCH|GERMAN)\b|[\[(_.]GER[\])_.]|[\[(_.]DE[\])_.]',
    re.IGNORECASE,
)
_ENG_RE = re.compile(
    r'\b(ENG|eng|english|ENGLISH)\b|[\[(_.]EN[\])_.]',
    re.IGNORECASE,
)
_ANIME_RE = re.compile(
    r'\b(ANIME|anime|SUB|SUBBED|VOSTFR|vostfr|MULTI)\b',
    re.IGNORECASE,
)
_DUBBED_RE = re.compile(r'\b(DUBBED|dubbed|DOPPELATO|doppelato|DUB)\b', re.IGNORECASE)
_4K_RE = re.compile(r'\b(2160p|4K|UHD|uhd)\b', re.IGNORECASE)
_1080_RE = re.compile(r'\b1080p\b', re.IGNORECASE)
_720_RE = re.compile(r'\b720p\b', re.IGNORECASE)
_DEBRID_RE = re.compile(
    r'\b(debrid|alldebrid|real[\-_]debrid|premiumize|torbox|offcloud)\b',
    re.IGNORECASE,
)

# ── Test title catalogue ──────────────────────────────────────────────────────

_STREMIO_MOVIE_TESTS = [
    {"imdb": "tt0382932", "name": "Ratatouille",    "lang": "ita"},
    {"imdb": "tt1375666", "name": "Inception",       "lang": "ita"},
    {"imdb": "tt0816692", "name": "Interstellar",    "lang": "ita"},
    {"imdb": "tt3659388", "name": "The Martian",     "lang": "ita"},
    {"imdb": "tt0120689", "name": "The Green Mile",  "lang": "ger"},
    {"imdb": "tt0109830", "name": "Forrest Gump",    "lang": "ger"},
    {"imdb": "tt5753856", "name": "Dark",            "lang": "ger"},
    {"imdb": "tt0245429", "name": "Spirited Away",   "lang": "anime"},
    {"imdb": "tt15398776","name": "Oppenheimer",     "lang": "multi"},
    {"imdb": "tt9362722", "name": "Spider-Verse",    "lang": "multi"},
]

_STREMIO_SERIES_TESTS = [
    {"imdb": "tt0944947", "name": "Game of Thrones", "s": 1, "e": 1, "lang": "ita"},
    {"imdb": "tt5753856", "name": "Dark",             "s": 1, "e": 1, "lang": "ger"},
    {"imdb": "tt2442560", "name": "Peaky Blinders",   "s": 1, "e": 1, "lang": "ita"},
    {"imdb": "tt0988824", "name": "Naruto",           "s": 1, "e": 1, "lang": "anime"},
    {"imdb": "tt13622776","name": "The Last of Us",   "s": 1, "e": 1, "lang": "multi"},
]

_TORZNAB_QUERIES = [
    {"q": "inception",          "cat": "2000", "lang": "ita"},
    {"q": "inception italiano", "cat": "2000", "lang": "ita"},
    {"q": "dark deutsch",       "cat": "5000", "lang": "ger"},
    {"q": "ratatouille ita",    "cat": "2000", "lang": "ita"},
    {"q": "forrest gump german","cat": "2000", "lang": "ger"},
    {"q": "naruto anime",       "cat": "5070", "lang": "anime"},
]

# Mini = 3 queries for on-discovery pass
_MINI_STREMIO_MOVIES  = [_STREMIO_MOVIE_TESTS[0], _STREMIO_MOVIE_TESTS[4], _STREMIO_MOVIE_TESTS[7]]
_MINI_STREMIO_SERIES  = [_STREMIO_SERIES_TESTS[0]]
_MINI_TORZNAB         = [_TORZNAB_QUERIES[0], _TORZNAB_QUERIES[2], _TORZNAB_QUERIES[5]]

_TIMEOUT = 10.0


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class RawBenchmarkResult:
    is_online: bool = False
    response_ms: int = 0
    total_results: int = 0
    italian_results: int = 0
    german_results: int = 0
    english_results: int = 0
    anime_results: int = 0
    dubbed_results: int = 0
    results_4k: int = 0
    results_1080p: int = 0
    results_720p: int = 0
    has_debrid_links: bool = False
    italian_score: float = 0.0
    german_score: float = 0.0
    anime_score: float = 0.0
    overall_score: float = 0.0
    test_queries_run: list = field(default_factory=list)
    raw_sample: list = field(default_factory=list)


# ── Score calculation ─────────────────────────────────────────────────────────

def _calc_scores(r: RawBenchmarkResult) -> RawBenchmarkResult:
    total = max(r.total_results, 1)
    availability = 100.0 if r.is_online else 0.0

    boost_ita   = 2.0 if r.italian_results > 10 else 1.0
    boost_ger   = 2.0 if r.german_results  > 10 else 1.0
    boost_anime = 2.0 if r.anime_results   > 10 else 1.0

    r.italian_score = round(min(100.0, r.italian_results / total * 100 * boost_ita),   2)
    r.german_score  = round(min(100.0, r.german_results  / total * 100 * boost_ger),   2)
    r.anime_score   = round(min(100.0, r.anime_results   / total * 100 * boost_anime), 2)

    r.overall_score = round(
        r.italian_score * 0.35 +
        r.german_score  * 0.25 +
        r.anime_score   * 0.15 +
        availability    * 0.25,
        2,
    )
    return r


# ── Text scanner ─────────────────────────────────────────────────────────────

def _scan(text: str, r: RawBenchmarkResult) -> None:
    if not text.strip():
        return
    r.total_results += 1
    if _ITA_RE.search(text):    r.italian_results += 1
    if _GER_RE.search(text):    r.german_results  += 1
    if _ENG_RE.search(text):    r.english_results += 1
    if _ANIME_RE.search(text):  r.anime_results   += 1
    if _DUBBED_RE.search(text): r.dubbed_results  += 1
    if _4K_RE.search(text):     r.results_4k      += 1
    if _1080_RE.search(text):   r.results_1080p   += 1
    if _720_RE.search(text):    r.results_720p    += 1
    if _DEBRID_RE.search(text): r.has_debrid_links = True
    if len(r.raw_sample) < 5:
        r.raw_sample.append(text[:200])


# ── Stremio benchmarker ───────────────────────────────────────────────────────

def _stremio_base(url: str) -> str:
    """Normalise a stremio URL to the base path (strip manifest.json suffix)."""
    base = url.rstrip("/")
    if base.endswith("/manifest.json"):
        base = base[: -len("/manifest.json")]
    return base


async def benchmark_stremio(url: str, mini: bool = True) -> RawBenchmarkResult:
    r = RawBenchmarkResult()
    base = _stremio_base(url)
    movie_tests  = _MINI_STREMIO_MOVIES  if mini else _STREMIO_MOVIE_TESTS
    series_tests = _MINI_STREMIO_SERIES  if mini else _STREMIO_SERIES_TESTS

    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT, follow_redirects=True, verify=False,
            headers={"User-Agent": "PascalHub/0.5 Benchmark"},
        ) as client:
            # Ping manifest
            try:
                mr = await client.get(f"{base}/manifest.json")
                r.is_online = mr.status_code == 200
            except Exception:
                pass

            for test in movie_tests:
                endpoint = f"{base}/stream/movie/{test['imdb']}.json"
                r.test_queries_run.append(endpoint)
                try:
                    resp = await client.get(endpoint)
                    if resp.status_code == 200:
                        r.is_online = True
                        for stream in resp.json().get("streams", []):
                            text = " ".join(filter(None, [
                                stream.get("title"),
                                stream.get("name"),
                                stream.get("description"),
                                (stream.get("behaviorHints") or {}).get("filename"),
                            ]))
                            _scan(text, r)
                except Exception:
                    pass

            for test in series_tests:
                endpoint = f"{base}/stream/series/{test['imdb']}:{test['s']}:{test['e']}.json"
                r.test_queries_run.append(endpoint)
                try:
                    resp = await client.get(endpoint)
                    if resp.status_code == 200:
                        r.is_online = True
                        for stream in resp.json().get("streams", []):
                            text = " ".join(filter(None, [
                                stream.get("title"),
                                stream.get("name"),
                                stream.get("description"),
                                (stream.get("behaviorHints") or {}).get("filename"),
                            ]))
                            _scan(text, r)
                except Exception:
                    pass

    except Exception:
        pass

    r.response_ms = int((time.monotonic() - t0) * 1000)
    return _calc_scores(r)


# ── Torznab / Newznab benchmarker ─────────────────────────────────────────────

def _torznab_api(url: str) -> str:
    """Return clean API endpoint URL (strip query string)."""
    return url.split("?")[0].rstrip("/")


async def benchmark_torznab(url: str, mini: bool = True) -> RawBenchmarkResult:
    r = RawBenchmarkResult()
    api = _torznab_api(url)
    queries = _MINI_TORZNAB if mini else _TORZNAB_QUERIES

    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT, follow_redirects=True, verify=False,
            headers={"User-Agent": "PascalHub/0.5 Benchmark"},
        ) as client:
            # Caps check
            try:
                caps = await client.get(f"{api}?t=caps")
                r.is_online = caps.status_code == 200
            except Exception:
                pass

            for q in queries:
                params: dict = {"t": "search", "q": q["q"]}
                if q.get("cat"):
                    params["cat"] = q["cat"]
                r.test_queries_run.append(f"{api}?t=search&q={q['q']}")
                try:
                    resp = await client.get(api, params=params)
                    if resp.status_code == 200:
                        try:
                            tree = etree.fromstring(resp.content)
                            for item in tree.findall(".//item"):
                                title_el = item.find("title")
                                desc_el  = item.find("description")
                                text = (
                                    (title_el.text or "" if title_el is not None else "") + " " +
                                    (desc_el.text  or "" if desc_el  is not None else "")
                                )
                                _scan(text, r)
                        except Exception:
                            pass
                except Exception:
                    pass

    except Exception:
        pass

    r.response_ms = int((time.monotonic() - t0) * 1000)
    return _calc_scores(r)


# ── Generic ping ─────────────────────────────────────────────────────────────

async def benchmark_generic(url: str) -> RawBenchmarkResult:
    r = RawBenchmarkResult()
    r.test_queries_run = [url]
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT, follow_redirects=True, verify=False,
        ) as client:
            resp = await client.get(url)
            r.is_online = resp.status_code < 400
    except Exception:
        pass
    r.response_ms = int((time.monotonic() - t0) * 1000)
    r.overall_score = 25.0 if r.is_online else 0.0
    return r


# ── Entry point ───────────────────────────────────────────────────────────────

_STREMIO_TYPES = frozenset({
    "stremio_manifest", "torrentio_family", "comet_family",
    "mediafusion_family", "stremthru_family", "aiostreams_family",
})
_TORZNAB_TYPES = frozenset({
    "torznab", "newznab", "jackett", "prowlarr", "nzbhydra", "bitmagnet",
})


async def benchmark_source(url: str, detected_type: str, mini: bool = True) -> RawBenchmarkResult:
    if detected_type in _STREMIO_TYPES:
        return await benchmark_stremio(url, mini=mini)
    if detected_type in _TORZNAB_TYPES:
        return await benchmark_torznab(url, mini=mini)
    return await benchmark_generic(url)
