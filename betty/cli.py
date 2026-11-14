"""Betty Better Eater: friendly command line.

  betty score 0096619533602              score one product (barcode)
  betty find "organic quinoa"            search by name and score the results
  betty better 0096619533602             find better-scoring alternatives
  betty browse oats --store costco       browse a category at a retailer
  betty categories                       list category shortcuts
  betty explain                          how the score works

Common options:
  --store costco       retailer (as tagged on Open Food Facts; e.g. costco, walmart, loblaws)
  --country canada     country where it's sold
  --diet halal,gluten-free   any mix of: halal, halal-strict, kosher, vegan, vegetarian, pescatarian,
                       no-pork, no-beef, no-alcohol, gluten-free, gluten-free-strict, lactose-free,
                       dairy-free, nut-free, peanut-free, egg-free, soy-free, sesame-free, fish-free,
                       shellfish-free, mustard-free, no-added-sugar, palm-oil-free   (betty diets)
  --min 90             your own minimum score (0-100)
  --band excellent     or a band: excellent (90+), very-good (75+), good (50+), bad (25+), very-bad
  --organic            organic products only
  --report list.html   save a printable shopping list with photos
  --json               machine-readable output
"""
import argparse, json, re, sys

from . import off
from .categories import SHORTCUTS, resolve
from .score import BANDS, band_floor
from .diet import passes, DIETS

GUIDE_WARNING = ("GUIDE ONLY: Betty is a helpful guide, not a guarantee. Always read the label yourself to "
                 "confirm ingredients, allergens and certifications. What you buy and eat is your own decision "
                 "and at your own discretion.")
DISCLAIMER = ("Scores are independent estimates based on Yuka's published method, not official Yuka scores. "
              "Data: Open Food Facts contributors (ODbL), which can be incomplete or out of date. "
              "Not medical, allergy or religious advice.\n" + GUIDE_WARNING)


def _diet(s):
    d = {x.strip().lower() for x in (s or "").split(",") if x.strip()}
    bad = d - set(DIETS)
    if bad:
        sys.exit(f"Unknown diet option(s): {', '.join(sorted(bad))}. Run `betty diets` to see them all.")
    return d


def _threshold(a):
    floor = 0
    if a.band:
        try:
            floor = band_floor(a.band)
        except ValueError as e:
            sys.exit(str(e))
    if a.min is not None:
        if not 0 <= a.min <= 100:
            sys.exit("--min must be between 0 and 100")
        floor = max(floor, a.min)
    return floor


def _line(r):
    notes = []
    if r["organic"]:
        notes.append("organic")
    if r["capped"]:
        notes.append(f"capped: {r['capped']}")
    if r["flagged_additives"]:
        notes.append("check additives " + ",".join(a.upper() for a in r["flagged_additives"]))
    notes += r["warnings"]
    name = (r["name"] or "?")[:44]
    brand = (r["brands"] or "")[:20]
    fits = ("Fits: " + " · ".join(r["fits"])) if r["fits"] else ""
    extra = f"  ({'; '.join(notes)})" if notes else ""
    return (f"{r['score']:>3}  {r['label']:<9}  {name:<44}  {brand:<20}  {r['code']}\n"
            f"{'':16}{fits}{extra}")


def _show(results, a, title):
    if a.json:
        print(json.dumps(results, indent=1, ensure_ascii=False))
        return
    print(f"\n{title}\n" + "-" * len(title))
    if not results:
        print("Nothing matched. Try fewer filters, a broader category, --pages 3, or another --country/--store.\n"
              "(If you expected results, Open Food Facts may be busy: wait a minute and try again.)")
    for r in results:
        print(_line(r))
    print(f"\n{len(results)} product(s). {DISCLAIMER}")
    if a.report:
        from .report import write_html
        write_html(a.report, results, title)
        print(f"Saved printable list: {a.report}")


def _filter(products, a):
    floor, diet, out, seen = _threshold(a), _diet(a.diet), [], set()
    for p in products:
        if p.get("code") in seen:
            continue
        seen.add(p.get("code"))
        r = off.evaluate(p)
        if not r or r["score"] < floor or not passes(r["diet"], diet):
            continue
        if a.organic and not r["organic"]:
            continue
        out.append(r)
    out.sort(key=lambda r: (-r["score"], r["name"] or ""))
    return out[: a.limit]


def _fetch(a, **kw):
    prods = []
    for page in range(1, a.pages + 1):
        batch = off.search(country=a.country, store=a.store, organic=a.organic, page=page, **kw)
        prods += batch
        if len(batch) < 100:
            break
    return prods


def cmd_score(a):
    if not a.product.isdigit():
        a.terms = a.product
        return cmd_find(a)
    p = off.product(a.product)
    if not p:
        sys.exit(f"Barcode {a.product} isn't on Open Food Facts yet. You can add it at "
                 f"https://world.openfoodfacts.org (it helps everyone).")
    r = off.evaluate(p)
    if not r:
        sys.exit(f"Found '{p.get('product_name')}', but it has no nutrition facts on Open Food Facts yet, "
                 f"so it can't be scored. Adding them takes a minute: https://world.openfoodfacts.org/product/{a.product}")
    if a.json:
        print(json.dumps(r, indent=1, ensure_ascii=False)); return
    print(f"\n{r['name']} ({r['brands']}) {r['quantity'] or ''}")
    print(f"  Estimated score : {r['score']}/100 ({r['label']})")
    print(f"  Nutrition       : {r['nutrition_rating']}/100 (Nutri-Score points {r['nutriscore_points']:+d}; {r['nutrition_source']})")
    print(f"  Additives       : {r['additive_rating']}/100 " +
          (f"(check: {', '.join(x.upper() for x in r['flagged_additives'])})" if r['flagged_additives'] else "(none of concern)"))
    print(f"  Organic         : {'yes' if r['organic'] else 'no (max possible score is 90)'}")
    if r["capped"]:
        print(f"  Capped at 49    : {r['capped']}")
    if r["fits"]:
        print(f"  Fits            : {' · '.join(r['fits'])}")
    if r["warnings"]:
        print(f"  Heads-up        : {'; '.join(r['warnings'])}")
    print(f"  Open Food Facts : {r['url']}\n\n{DISCLAIMER}")
    if a.report:
        from .report import write_html
        write_html(a.report, [r], r["name"] or a.product); print(f"Saved: {a.report}")


def cmd_find(a):
    terms = a.terms if hasattr(a, "terms") and a.terms else a.query
    prods = []
    for page in range(1, a.pages + 1):
        batch = off.search(terms=terms, country=a.country, store=a.store, organic=a.organic, page=page)
        prods += batch
        if len(batch) < 100:
            break
    _show(_filter(prods, a), a, f'Results for "{terms}"' + _where(a))


def cmd_better(a):
    if a.product.isdigit():
        p = off.product(a.product)
    else:
        hits = off.search(terms=a.product, country=a.country, page_size=10)
        p = hits[0] if hits else {}
    if not p:
        sys.exit("Couldn't find that product on Open Food Facts. Try the barcode instead.")
    base = off.evaluate(p)
    cats = similar_categories(p)
    if not cats:
        sys.exit("That product has no specific category on Open Food Facts, so alternatives can't be matched. "
                 "Try `betty browse <category>` instead.")
    print(f"\nLooking for something better than: {p.get('product_name')} "
          f"({base['score'] if base else '?'}/100)")
    results, cat, tried = [], cats[0], 0
    for cat in cats[:6]:          # its own category, then at most one level broader
        prods = _fetch(a, category=cat)
        if not prods:
            continue              # nothing in this category here (yet); try the next one
        tried += 1
        results = [r for r in _filter(prods, a)
                   if r["code"] != p.get("code") and (not base or r["score"] > base["score"])]
        if results or tried >= 2:
            break
    _show(results, a, f"Better alternatives in '{cat.split(':', 1)[-1].replace('-', ' ')}'" + _where(a))


# Catch-all categories that would compare guacamole with parsley
GENERIC = {"en:groceries", "en:foods", "en:plant-based-foods-and-beverages", "en:plant-based-foods",
           "en:beverages", "en:beverages-and-beverages-preparations", "en:snacks", "en:sweet-snacks",
           "en:salty-snacks", "en:condiments", "en:sauces", "en:spreads", "en:dairies", "en:meats",
           "en:meats-and-their-products", "en:frozen-foods", "en:canned-foods", "en:dried-products",
           "en:cereals-and-potatoes", "en:fruits-and-vegetables-based-foods", "en:breakfasts",
           "en:desserts", "en:meals", "en:seafood", "en:fermented-foods", "en:fermented-milk-products",
           "en:farming-products", "en:dried-products-to-be-rehydrated", "en:dietary-supplements"}

CATEGORY_TAG = re.compile(r"^[a-z]{2}:[a-z0-9-]+$")


def similar_categories(p):
    """Most specific category first; never a catch-all one."""
    cats = p.get("categories_hierarchy") or p.get("categories_tags") or []
    out = []
    for c in reversed(cats):
        if not CATEGORY_TAG.match(c):
            continue                       # e.g. "fr:Nutella": a brand typed as a category
        if c not in GENERIC and c not in out:
            out.append(c)
    return out


def cmd_browse(a):
    cat = resolve(a.category)
    _show(_filter(_fetch(a, category=cat, brand=a.brand), a), a,
          f"{cat.split(':', 1)[-1].replace('-', ' ').title()}" + _where(a))


def cmd_categories(a):
    print("Category shortcuts (any Open Food Facts category tag also works, e.g. en:canned-chickpeas):\n")
    for k, v in sorted(SHORTCUTS.items()):
        print(f"  {k:<18} -> {v}")


def cmd_diets(a):
    print("Diet options for --diet (combine with commas, e.g. --diet halal,gluten-free,nut-free):\n")
    for k, (label, _, _) in DIETS.items():
        print(f"  {k:<20} {label}")
    print("\nFree-from filters are cautious: products without an ingredient list, or with a 'may contain'"
          "\nwarning, are left out. For allergies and religious needs, ALWAYS check the pack yourself.\n\n"
          + GUIDE_WARNING)


def cmd_explain(a):
    print("""
How Betty estimates a score (0-100), following Yuka's published method:
  60%  Nutrition: Nutri-Score (original 2017 algorithm) converted with Yuka's table
  30%  Additives: risk-free additives cost nothing; any high-risk additive caps the product at 49
  10%  Organic: bonus for an official organic label (so non-organic products max out at 90)
  Nutri-Score D/E products never exceed 49.

Bands: """ + ", ".join(f"{n} {f}+" for n, f in BANDS[:-1]) + """, Very bad below 25.
Set your own bar with --min (e.g. --min 85) or --band (e.g. --band very-good).
""" + DISCLAIMER)


def _where(a):
    bits = [x for x in [a.store and f"at {a.store}", a.country and f"in {a.country}"] if x]
    return (" " + " ".join(bits)) if bits else ""


def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--store", help="retailer, e.g. costco, walmart, loblaws, tesco")
    common.add_argument("--country", help="country, e.g. canada, united-states, france")
    common.add_argument("--diet", help="comma list, e.g. halal,gluten-free,nut-free (see: betty diets)")
    common.add_argument("--min", type=int, help="your own minimum score, 0-100")
    common.add_argument("--band", help="excellent | very-good | good | bad | very-bad")
    common.add_argument("--organic", action="store_true", help="organic products only")
    common.add_argument("--limit", type=int, default=30, help="max results to show (default 30)")
    common.add_argument("--pages", type=int, default=1, help="pages of 100 products to scan (default 1)")
    common.add_argument("--report", help="save a printable HTML shopping list, e.g. list.html")
    common.add_argument("--json", action="store_true", help="JSON output")

    ap = argparse.ArgumentParser(prog="betty", description="Betty Better Eater: find healthier groceries.",
                                 epilog="Example: betty browse oats --country canada --store costco --band excellent")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score", parents=[common], help="score one product (barcode or name)")
    s.add_argument("product"); s.set_defaults(fn=cmd_score)
    s = sub.add_parser("find", parents=[common], help="search by name")
    s.add_argument("query"); s.set_defaults(fn=cmd_find)
    s = sub.add_parser("better", parents=[common], help="find better alternatives to a product")
    s.add_argument("product"); s.set_defaults(fn=cmd_better)
    s = sub.add_parser("browse", parents=[common], help="browse a category")
    s.add_argument("category"); s.add_argument("--brand", help="limit to a brand, e.g. kirkland-signature")
    s.set_defaults(fn=cmd_browse)
    sub.add_parser("categories", help="list category shortcuts").set_defaults(fn=cmd_categories)
    sub.add_parser("diets", help="list diet & allergy filters").set_defaults(fn=cmd_diets)
    sub.add_parser("explain", help="how the score works").set_defaults(fn=cmd_explain)
    if argv is None:
        argv = sys.argv[1:]
    if not argv:                                   # no arguments: guided mode
        from .interactive import run
        argv = run()
    a = ap.parse_args(argv)
    for k in ("store", "country", "diet", "min", "band", "organic", "limit", "pages", "report", "json"):
        if not hasattr(a, k):
            setattr(a, k, None)
    a.limit = a.limit or 30
    a.pages = max(1, min(a.pages or 1, 10))
    a.fn(a)


if __name__ == "__main__":
    main()
