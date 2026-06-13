"""Small local symbol catalog and search helpers.

This is intentionally lightweight. A broker or KRX master-file importer can
replace the seed list later, while the API contract remains stable.
"""

from core.database import row_to_dict


DEFAULT_KRX_SYMBOLS = [
    {"market": "KRX", "code": "005930", "name": "삼성전자", "aliases": ["Samsung Electronics", "삼전"]},
    {"market": "KRX", "code": "000660", "name": "SK하이닉스", "aliases": ["SK hynix", "하이닉스"]},
    {"market": "KRX", "code": "035420", "name": "NAVER", "aliases": ["네이버"]},
    {"market": "KRX", "code": "035720", "name": "카카오", "aliases": ["Kakao"]},
    {"market": "KRX", "code": "005380", "name": "현대차", "aliases": ["Hyundai Motor"]},
    {"market": "KRX", "code": "000270", "name": "기아", "aliases": ["Kia"]},
    {"market": "KRX", "code": "373220", "name": "LG에너지솔루션", "aliases": ["LG Energy Solution"]},
    {"market": "KRX", "code": "051910", "name": "LG화학", "aliases": ["LG Chem"]},
    {"market": "KRX", "code": "006400", "name": "삼성SDI", "aliases": ["Samsung SDI"]},
    {"market": "KRX", "code": "207940", "name": "삼성바이오로직스", "aliases": ["Samsung Biologics"]},
    {"market": "KRX", "code": "068270", "name": "셀트리온", "aliases": ["Celltrion"]},
    {"market": "KRX", "code": "105560", "name": "KB금융", "aliases": ["KB Financial"]},
    {"market": "KRX", "code": "055550", "name": "신한지주", "aliases": ["Shinhan"]},
    {"market": "KRX", "code": "012330", "name": "현대모비스", "aliases": ["Hyundai Mobis"]},
    {"market": "KRX", "code": "028260", "name": "삼성물산", "aliases": ["Samsung C&T"]},
    {"market": "KRX", "code": "066570", "name": "LG전자", "aliases": ["LG Electronics"]},
    {"market": "KRX", "code": "003550", "name": "LG", "aliases": []},
    {"market": "KRX", "code": "034020", "name": "두산에너빌리티", "aliases": ["Doosan Enerbility"]},
    {"market": "KRX", "code": "042700", "name": "한미반도체", "aliases": ["Hanmi Semiconductor"]},
    {"market": "KRX", "code": "086520", "name": "에코프로", "aliases": ["EcoPro"]},
    {"market": "KRX", "code": "247540", "name": "에코프로비엠", "aliases": ["EcoPro BM"]},
    {"market": "KRX", "code": "069500", "name": "KODEX 200", "aliases": ["코덱스200"]},
    {"market": "KRX", "code": "229200", "name": "KODEX 코스닥150", "aliases": ["코덱스 코스닥150"]},
]


def search_symbols(conn, query="", market="KRX", limit=20):
    query = (query or "").strip()
    market = (market or "KRX").strip().upper()
    candidates = _db_symbols(conn, market) + DEFAULT_KRX_SYMBOLS
    deduped = {}
    for item in candidates:
        if item.get("market", "").upper() != market:
            continue
        key = (item["market"], item["code"])
        current = deduped.get(key, {})
        merged = dict(current)
        merged.update(item)
        merged.setdefault("aliases", current.get("aliases", []))
        deduped[key] = merged

    if not query:
        return [_public_symbol(item) for item in list(deduped.values())[:limit]]

    normalized_query = _normalize(query)
    scored = []
    for item in deduped.values():
        score = _score_symbol(item, normalized_query)
        if score is not None:
            scored.append((score, item["code"], item))
    scored.sort(key=lambda row: (row[0], row[1]))
    return [_public_symbol(item) for _, _, item in scored[:limit]]


def resolve_symbol(conn, market, code, name=None):
    market = (market or "KRX").strip().upper()
    code = (code or "").strip()
    row = conn.execute(
        "SELECT market, code, name, currency, provider, enabled FROM market_symbols WHERE market = ? AND code = ?",
        (market, code),
    ).fetchone()
    if row:
        return _public_symbol(row_to_dict(row))
    for item in DEFAULT_KRX_SYMBOLS:
        if item["market"] == market and item["code"] == code:
            return _public_symbol(item)
    return {"market": market, "code": code, "name": name or code, "currency": "KRW", "provider": "manual"}


def _db_symbols(conn, market):
    rows = conn.execute(
        """
        SELECT market, code, name, currency, provider, enabled
        FROM market_symbols
        WHERE market = ? AND enabled = 1
        ORDER BY code
        """,
        (market,),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def _score_symbol(item, normalized_query):
    code = _normalize(item.get("code", ""))
    name = _normalize(item.get("name", ""))
    aliases = [_normalize(alias) for alias in item.get("aliases", [])]
    texts = [code, name] + aliases
    if normalized_query == code:
        return 0
    if code.startswith(normalized_query):
        return 1
    if normalized_query == name:
        return 2
    if any(normalized_query == alias for alias in aliases):
        return 3
    if normalized_query in name:
        return 4
    if any(normalized_query in alias for alias in aliases):
        return 5
    if any(normalized_query in text for text in texts):
        return 6
    return None


def _public_symbol(item):
    return {
        "market": item.get("market", "KRX"),
        "code": item["code"],
        "name": item.get("name", item["code"]),
        "currency": item.get("currency", "KRW"),
        "provider": item.get("provider", "catalog"),
    }


def _normalize(value):
    return "".join(str(value or "").lower().split())
