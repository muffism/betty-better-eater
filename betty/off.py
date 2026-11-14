"""Small, polite Open Food Facts client.

Open Food Facts asks API users to: send a descriptive User-Agent, stay under
~100 product reads/min and ~10 searches/min, and credit the data (ODbL).
https://openfoodfacts.github.io/openfoodfacts-server/api/
"""
import json, os, time, hashlib
import requests

from .nutriscore import Nutrition, points as ns_points
from .score import estimate
from .additives import risks
from .diet import classify, badges, warnings
from . import local

UA = {"User-Agent": "BettyBetterEater/0.3 (+https://github.com/muffism/betty-better-eater)"}
BASE = "https://world.openfoodfacts.org"
FIELDS = ("code,product_name,product_name_en,brands,quantity,stores,stores_tags,countries_tags,labels_tags,"
          "categories_tags,categories_hierarchy,ingredients_text,ingredients_text_en,additives_tags,"
          "ingredients_analysis_tags,allergens_tags,traces_tags,nutriments,nutriscore,nutrition_grades,image_front_url,"
          "image_front_small_url,url")
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "betty", "off")
_last = {"search": 0.0, "read": 0.0}
_gap = {"search": 6.5, "read": 0.7}   # seconds between calls (10/min search, ~85/min read)


def _throttle(kind):
    wait = _gap[kind] - (time.time() - _last[kind])
    if wait > 0:
        time.sleep(wait)
    _last[kind] = time.time()


def _get(url, params, kind, ttl=7 * 86400):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha1((url + json.dumps(params, sort_keys=True)).encode()).hexdigest()
    path = os.path.join(CACHE, key + ".json")
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < ttl:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    for attempt in range(4):
        _throttle(kind)
        try:
            r = requests.get(url, params=params, headers=UA, timeout=45)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(10 * (attempt + 1)); continue
            data = r.json()
            # only cache real answers; an empty/odd reply may just mean OFF is busy
            if data.get("product") or data.get("products"):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f)
            return data
        except (requests.RequestException, ValueError):
            time.sleep(5 * (attempt + 1))
    return {}


def product(barcode: str, prefer_online=False) -> dict:
    """One product by barcode. Uses the offline database when there is one (falls back to the internet)."""
    if not prefer_online:
        hit = local.product(barcode)
        if hit:
            return hit
    p = _get(f"{BASE}/api/v2/product/{barcode}", {"fields": FIELDS}, "read").get("product") or {}
    return p or (local.product(barcode) if prefer_online else {})


def search(*, terms=None, category=None, country=None, store=None, brand=None, organic=False,
           page_size=100, page=1) -> list:
    """Filter-based search. country/store/brand/category are Open Food Facts tags,
    e.g. country='canada', store='costco', category='en:breakfast-cereals'.
    Answered from the offline database when it covers that country (instant)."""
    if local.covers(country):
        return local.search(terms=terms, category=category, store=store, brand=brand, organic=organic, page=page)
    p = {"fields": FIELDS, "page_size": page_size, "page": page, "sort_by": "unique_scans_n"}
    if category:
        p["categories_tags"] = category if ":" in category else "en:" + category
    if country:
        p["countries_tags_en"] = country
    if store:
        p["stores_tags"] = store.lower().replace(" ", "-")
    if brand:
        p["brands_tags"] = brand.lower().replace(" ", "-")
    if organic:
        p["labels_tags"] = "en:organic"
    if terms:
        # full-text search lives on the legacy endpoint
        p.update({"search_terms": terms, "search_simple": 1, "action": "process", "json": 1})
        return _get(f"{BASE}/cgi/search.pl", p, "search").get("products", [])
    return _get(f"{BASE}/api/v2/search", p, "search").get("products", [])


# ---------------------------------------------------------------- scoring
BEVERAGE_CATS = {"en:beverages", "en:plant-based-beverages"}
NOT_BEVERAGE = {"en:milks", "en:dairy-drinks", "en:plant-milks"}  # 2017 rule: milk scored as food


ORGANIC_LABELS = ("en:organic", "en:eu-organic", "en:usda-organic", "en:canada-organic",
                  "fr:ab-agriculture-biologique")


def is_organic(p):
    labels = p.get("labels_tags") or []
    return any(t in labels for t in ORGANIC_LABELS)


def to_nutrition(p) -> Nutrition | None:
    n = p.get("nutriments") or {}
    if "energy-kcal_100g" not in n and "energy_100g" not in n:
        return None
    kcal = n.get("energy-kcal_100g") or (n.get("energy_100g", 0) / 4.184)
    fvn = (n.get("fruits-vegetables-legumes-estimate-from-ingredients_100g")
           or n.get("fruits-vegetables-nuts-estimate-from-ingredients_100g") or 0)
    return Nutrition(kcal=kcal, sugars=n.get("sugars_100g", 0) or 0,
                     sat_fat=n.get("saturated-fat_100g", 0) or 0,
                     sodium_mg=(n.get("sodium_100g", 0) or 0) * 1000,
                     fibre=n.get("fiber_100g", 0) or 0, protein=n.get("proteins_100g", 0) or 0,
                     fvn_pct=fvn, fat=n.get("fat_100g"))


def evaluate(p: dict) -> dict | None:
    """Score one Open Food Facts product. Returns None if nutrition is missing."""
    cats = set(p.get("categories_tags") or [])
    beverage = bool(cats & BEVERAGE_CATS) and not (cats & NOT_BEVERAGE)
    if "en:waters" in cats:
        return None                          # Yuka rates water on a separate scale
    ns = ((p.get("nutriscore") or {}).get("2021") or {})
    pts = ns.get("score") if (ns.get("nutriscore_computed") and ns.get("score") is not None) else None
    source = "Open Food Facts (Nutri-Score 2021 field = original algorithm)"
    if pts is None:
        nut = to_nutrition(p)
        if nut is None:
            return None
        pts = ns_points(nut, beverage=beverage, cheese="en:cheeses" in cats,
                        added_fat="en:fats" in cats)
        source = "computed by Betty from Open Food Facts nutrients"
    est = estimate(int(pts), is_organic(p), risks(p.get("additives_tags")), beverage=beverage)
    diet = classify(p)
    return dict(code=p.get("code"), name=p.get("product_name_en") or p.get("product_name"), brands=p.get("brands"),
                quantity=p.get("quantity"), stores=p.get("stores"),
                image=p.get("image_front_url") or p.get("image_front_small_url"),
                url=f"{BASE}/product/{p.get('code')}", score=est.score, label=est.label,
                nutriscore_points=int(pts), nutrition_rating=est.nutrition_rating,
                additive_rating=est.additive_rating, organic=est.organic,
                capped=est.capped_reason, flagged_additives=est.flagged_additives,
                beverage=beverage, nutrition_source=source, diet=diet, fits=badges(diet),
                warnings=warnings(diet),
                categories=p.get("categories_tags") or [])
