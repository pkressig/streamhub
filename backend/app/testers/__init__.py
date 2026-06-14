from app.testers.torznab import TorznabTester
from app.testers.newznab import NewznabTester
from app.testers.rss import RssTester
from app.testers.manifest import ManifestTester
from app.testers.generic_http import GenericHttpTester

TESTER_MAP = {
    "torznab": TorznabTester,
    "newznab": NewznabTester,
    "rss": RssTester,
    "manifest": ManifestTester,
    "generic_http": GenericHttpTester,
}

def get_tester(source_type: str):
    return TESTER_MAP.get(source_type, GenericHttpTester)()
