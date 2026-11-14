"""Offline mode: stream the full Open Food Facts CSV dump (~1.5 GB, never saved)
and keep only the products you care about, as a small TSV you can open in a spreadsheet.

  python scripts/off_filter_dump.py --country canada --store costco --out costco_canada.tsv
  python scripts/off_filter_dump.py --brand kirkland --out kirkland.tsv

Data: Open Food Facts contributors, Open Database License (ODbL). If you share the
filtered file, keep it under ODbL and credit Open Food Facts.
"""
import argparse, csv, gzip, io, sys
import requests

URL = "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"
KEEP = ["code", "product_name", "brands", "stores", "countries_tags", "labels_tags", "categories_tags",
        "ingredients_text", "additives_tags", "nutriscore_score", "nutriscore_grade", "energy-kcal_100g",
        "sugars_100g", "saturated-fat_100g", "sodium_100g", "fiber_100g", "proteins_100g",
        "fruits-vegetables-nuts-estimate-from-ingredients_100g", "image_url", "quantity"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--country", help="e.g. canada (matches en:canada)")
    ap.add_argument("--store", help="e.g. costco (substring of the stores field)")
    ap.add_argument("--brand", help="e.g. kirkland (substring of brands)")
    ap.add_argument("--out", default="off_filtered.tsv")
    a = ap.parse_args()
    if not (a.country or a.store or a.brand):
        sys.exit("Give at least one of --country, --store, --brand (the full dump has ~5 million products).")
    csv.field_size_limit(10**9)
    r = requests.get(URL, stream=True, timeout=120,
                     headers={"User-Agent": "BettyBetterEater/0.3 (+https://github.com/muffism/betty-better-eater)"})
    r.raise_for_status()
    rows = csv.DictReader(io.TextIOWrapper(gzip.GzipFile(fileobj=r.raw), encoding="utf-8", errors="replace",
                                           newline=""), delimiter="\t", quoting=csv.QUOTE_NONE)
    n = kept = 0
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, KEEP, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for row in rows:
            n += 1
            if a.country and f"en:{a.country.lower()}" not in (row.get("countries_tags") or ""):
                continue
            if a.store and a.store.lower() not in (row.get("stores") or "").lower():
                continue
            if a.brand and a.brand.lower() not in (row.get("brands") or "").lower():
                continue
            w.writerow(row); kept += 1
            if n % 500000 == 0:
                print(f"{n:,} scanned, {kept:,} kept", flush=True)
    print(f"Done: {n:,} products scanned, {kept:,} saved to {a.out}")
    print("Note: the CSV's nutriscore_score column uses the 2023 algorithm; Betty/Yuka use the original one.")


if __name__ == "__main__":
    main()
