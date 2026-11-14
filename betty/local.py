"""Fast offline mode: download Open Food Facts once, then search on your own PC.

The full Open Food Facts export (about 1.5 GB) is streamed once and never saved.
Only the products sold in your country are kept, in a small local database
(~/.cache/betty/products-<country>.db), so searches are instant and Open Food
Facts' servers are spared thousands of API calls.

Data: Open Food Facts contributors, Open Database License (ODbL).
"""
import csv, gzip, io, json, os, sqlite3, sys, time
from contextlib import closing

import requests

DUMP_URL = "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"
HOME = os.path.join(os.path.expanduser("~"), ".cache", "betty")
SETTINGS = os.path.join(HOME, "settings.json")
UA = {"User-Agent": "BettyBetterEater/0.3 (+https://github.com/muffism/betty-better-eater)"}
STALE_DAYS = 30
NUTRIENTS = ("energy-kcal_100g", "energy_100g", "fat_100g", "saturated-fat_100g", "sugars_100g", "sodium_100g",
             "fiber_100g", "proteins_100g")
LIST_TAGS = ("countries_tags", "labels_tags", "categories_tags", "additives_tags", "ingredients_analysis_tags",
             "traces_tags", "brands_tags")
DISABLED = False              # set by --online
MAX_RESULTS = 3000            # products scanned per search; plenty for one category in one country


# ---------------------------------------------------------------- settings
def settings() -> dict:
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(**kw):
    s = settings()
    s.update(kw)
    os.makedirs(HOME, exist_ok=True)
    with open(SETTINGS, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=1)


def slug(text: str) -> str:
    return "-".join((text or "").strip().lower().replace("_", " ").split())


def db_path(country: str) -> str:
    return os.path.join(HOME, f"products-{slug(country)}.db")


def active() -> dict | None:
    """The offline database in use, as {country, path, built, products}, or None (online mode)."""
    s = settings()
    c = s.get("offline_country")
    if DISABLED or s.get("mode") != "offline" or not c or not os.path.exists(db_path(c)):
        return None
    return {"country": c, "path": db_path(c), "built": s.get("offline_built", 0),
            "products": s.get("offline_products", 0)}


def age_days() -> int:
    a = active()
    return int((time.time() - a["built"]) / 86400) if a else 0


def dump_size() -> int:
    """Size of the Open Food Facts export in bytes (0 if it can't be checked)."""
    try:
        r = requests.head(DUMP_URL, allow_redirects=True, timeout=20, headers=UA)
        return int(r.headers.get("content-length") or 0)
    except (requests.RequestException, ValueError):
        return 0


def gb(n: int) -> str:
    return f"{n / 1e9:.1f} GB" if n else "about 1.5 GB"


# ---------------------------------------------------------------- CSV row -> product dict
def _num(v):
    if v in (None, ""):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _tags(v):
    return [t for t in (v or "").split(",") if t]


def to_product(row: dict) -> dict:
    """Turn one export row into the same shape the Open Food Facts API returns."""
    n = {k: _num(row.get(k)) for k in NUTRIENTS}
    n = {k: v for k, v in n.items() if v is not None}
    fvl = _num(row.get("fruits-vegetables-legumes_100g"))
    if fvl is not None:
        n["fruits-vegetables-legumes-estimate-from-ingredients_100g"] = fvl
    p = {"code": row.get("code"), "product_name": row.get("product_name"), "brands": row.get("brands"),
         "quantity": row.get("quantity"), "stores": row.get("stores"), "ingredients_text": row.get("ingredients_text"),
         "allergens_tags": _tags(row.get("allergens")), "nutriments": n,
         "image_front_url": row.get("image_url"), "image_front_small_url": row.get("image_small_url"),
         "stores_tags": [slug(s) for s in (row.get("stores") or "").split(",") if s.strip()]}
    for k in LIST_TAGS:
        p[k] = _tags(row.get(k))
    return {k: v for k, v in p.items() if v not in (None, "")}


def _wrap(items) -> str:
    """',a,b,' so a LIKE '%,a,%' matches whole tags only."""
    return "," + ",".join(items) + "," if items else ""


# ---------------------------------------------------------------- download
class _Counter(io.RawIOBase):
    """Counts compressed bytes so we can show real download progress."""

    def __init__(self, raw):
        self.raw, self.read_bytes = raw, 0

    def readable(self):
        return True

    def readinto(self, b):
        chunk = self.raw.read(len(b))
        n = len(chunk)
        b[:n] = chunk
        self.read_bytes += n
        return n


def download(country: str, url: str = DUMP_URL, out=sys.stdout) -> int:
    """Stream the export once, keep the products sold in `country`. Returns how many were kept."""
    country = slug(country)
    if not country:
        raise ValueError("pick a country, e.g. canada")
    tag = f"en:{country}"
    os.makedirs(HOME, exist_ok=True)
    final, tmp = db_path(country), db_path(country) + ".partial"
    if os.path.exists(tmp):
        os.remove(tmp)
    r = requests.get(url, stream=True, timeout=120, headers=UA)
    r.raise_for_status()
    total = int(r.headers.get("content-length") or 0)
    counter = _Counter(r.raw)
    csv.field_size_limit(2**31 - 1)
    rows = csv.DictReader(io.TextIOWrapper(gzip.GzipFile(fileobj=io.BufferedReader(counter, 1 << 20)),
                                           encoding="utf-8", errors="replace", newline=""),
                          delimiter="\t", quoting=csv.QUOTE_NONE)
    con = sqlite3.connect(tmp)
    con.execute("CREATE TABLE products (code TEXT PRIMARY KEY, name TEXT, brands TEXT, stores TEXT, "
                "categories TEXT, labels TEXT, scans INTEGER, json TEXT)")
    kept = scanned = 0
    shown = time.time()
    try:
        for row in rows:
            scanned += 1
            if tag not in (row.get("countries_tags") or ""):
                continue
            if tag not in _tags(row.get("countries_tags")):
                continue
            p = to_product(row)
            if not p.get("code"):
                continue
            con.execute("INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?,?,?)", (
                p["code"], (p.get("product_name") or "").lower(),
                (p.get("brands") or "").lower() + " " + _wrap(p.get("brands_tags")),
                _wrap(p.get("stores_tags")), _wrap(p.get("categories_tags")), _wrap(p.get("labels_tags")),
                int(_num(row.get("unique_scans_n")) or 0), json.dumps(p, ensure_ascii=False)))
            kept += 1
            if time.time() - shown > 2:
                shown = time.time()
                pct = f" ({100 * counter.read_bytes / total:.0f}%)" if total else ""
                print(f"\r  {counter.read_bytes / 1e6:,.0f} MB of {total / 1e6:,.0f} MB{pct} · "
                      f"{scanned:,} products checked · {kept:,} kept", end="", file=out, flush=True)
        con.commit()
    except BaseException:
        con.close()
        os.remove(tmp)
        raise
    con.close()
    print(f"\r  Done: {scanned:,} products checked, {kept:,} sold in {country} saved."
          + " " * 20, file=out, flush=True)
    os.replace(tmp, final)
    save_settings(mode="offline", offline_country=country, offline_built=time.time(), offline_products=kept)
    return kept


def remove():
    s = settings()
    c = s.get("offline_country")
    if c and os.path.exists(db_path(c)):
        os.remove(db_path(c))
    save_settings(mode="online", offline_country=None, offline_built=0, offline_products=0)


# ---------------------------------------------------------------- queries
def _con():
    a = active()
    return sqlite3.connect(a["path"]) if a else None


def product(code: str) -> dict:
    con = _con()
    if not con:
        return {}
    with closing(con):
        row = con.execute("SELECT json FROM products WHERE code = ?", (code,)).fetchone()
    return json.loads(row[0]) if row else {}


def covers(country: str | None) -> bool:
    """True when the offline database can answer a search for this country."""
    a = active()
    return bool(a) and (not country or slug(country) == a["country"])


def _fetch_store_codes(store: str, country: str) -> list:
    """Every barcode Open Food Facts tags with this store in this country (100 per polite search)."""
    from . import off                       # late import: off imports this module
    codes, page, pages = [], 1, 1
    while page <= min(pages, 40):
        data = off._get(f"{off.BASE}/api/v2/search", {"stores_tags": store, "countries_tags_en": country,
                                                      "fields": "code", "page_size": 100, "page": page}, "search")
        if not data:
            raise OSError("Open Food Facts didn't answer")
        if page == 1:
            pages = -(-int(data.get("count") or 0) // 100)
            if pages > 1:
                print(f"(Getting {store}'s product list from Open Food Facts once: about {pages * 7} seconds.)",
                      file=sys.stderr, flush=True)
        codes += [p["code"] for p in data.get("products") or [] if p.get("code")]
        page += 1
    return codes


def store_codes(store: str) -> set:
    """Barcodes sold at a store in the offline country.

    The export leaves the store blank for most products (the live site has them), so the list
    is fetched online once per store and kept for 30 days. Without internet: export data only."""
    a = active()
    store = slug(store)
    path = os.path.join(HOME, f"store-{a['country']}-{store}.json")
    try:
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
        if time.time() - saved["built"] < STALE_DAYS * 86400:
            return set(saved["codes"])
    except (OSError, ValueError, KeyError):
        saved = None
    try:
        codes = _fetch_store_codes(store, a["country"])
    except Exception:
        return set(saved["codes"]) if saved else set()
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"built": time.time(), "codes": codes}, f)
    return set(codes)


def search(*, terms=None, category=None, store=None, brand=None, organic=False, page=1, **_) -> list:
    if page > 1:
        return []                           # one local query already returns everything that matches
    con = _con()
    if not con:
        return []
    where, args = [], []
    if category:
        where.append("categories LIKE ?")
        args.append(f"%,{category if ':' in category else 'en:' + category},%")
    at_store = set()
    if store:
        at_store = store_codes(store)
        where.append("(stores LIKE ? OR code IN (SELECT value FROM json_each(?)))")
        args += [f"%,{slug(store)},%", json.dumps(sorted(at_store))]
    if brand:
        where.append("brands LIKE ?")
        args.append(f"%,{slug(brand)},%")
    if organic:
        where.append("labels LIKE ?")
        args.append("%,en:organic,%")
    for word in (terms or "").lower().split():
        where.append("(name LIKE ? OR brands LIKE ?)")
        args += [f"%{word}%", f"%{word}%"]
    sql = ("SELECT json FROM products" + (" WHERE " + " AND ".join(where) if where else "")
           + " ORDER BY scans DESC LIMIT ?")
    with closing(con):
        rows = con.execute(sql, args + [MAX_RESULTS]).fetchall()
    out = [json.loads(r[0]) for r in rows]
    for p in out:
        if p.get("code") in at_store and slug(store) not in (p.get("stores_tags") or []):
            p["stores"] = ", ".join(filter(None, [p.get("stores"), store.title()]))   # shown on the list
            p["stores_tags"] = (p.get("stores_tags") or []) + [slug(store)]
    return out
