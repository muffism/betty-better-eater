---
name: betty-better-eater
description: Find healthier groceries at the user's own store. Estimates Yuka-style 0-100 food scores (60% Nutri-Score, 30% additives, 10% organic) from Open Food Facts data, finds better alternatives, browses categories by retailer and country, and filters for halal / no-pork / no-beef / vegetarian / vegan. Use when someone asks things like "what's healthy at Costco", "is this product good", "find a better cereal", "Yuka score", "halal snacks at Walmart", or wants a shopping list (HTML/PDF) with product photos.
---

# Betty Better Eater

Betty is a small open-source Python CLI (`betty`) plus this playbook. Scores are **estimates** that follow
Yuka's *published* method. They are not official Yuka scores, so always say so.

## Setup (once)
```bash
pip install "git+https://github.com/muffism/betty-better-eater"   # or: pip install -e <repo folder>
betty explain                                                     # sanity check
```

## Pick the user's goal, then run one command
| User wants | Command |
|---|---|
| Score one product | `betty score <barcode or name> [--json]` |
| A better alternative | `betty better <barcode or name> --country X --store Y --diet ... --band very-good` |
| Browse a category | `betty browse <category> --country X --store Y --band excellent` (`betty categories` lists shortcuts; any OFF tag like `en:canned-chickpeas` works) |
| Search by name | `betty find "organic chickpeas" --country X --store Y` |
| Printable list | add `--report list.html` (photos from Open Food Facts, credited) |

**Thresholds:** the user's own `--min N` (e.g. 90) and/or `--band excellent|very-good|good|bad|very-bad`
(90+ / 75+ / 50+ / 25+ / below 25). Ask which they prefer if it isn't obvious. Don't assume 90.

**Diet:** `--diet halal` (certified, or no haram/doubtful ingredients and not meat), `halal-strict`
(certified label only), `no-pork`, `no-beef`, `vegetarian`, `vegan` (comma-separate). Meat always needs a
halal certificate to pass `halal`. Wine vinegar is flagged *doubtful* so the user can decide.

## Retailer of choice
- `--store` uses Open Food Facts' crowd-sourced store tags. Coverage varies: Costco, Walmart and Tesco are good;
  small chains are thin. If results are sparse, run without `--store` (same country), then **check that
  the retailer actually sells the top picks**, by looking at the retailer's public product pages with normal
  browsing or web search, a few pages at a time. Never bulk-scrape a retailer or bypass bot protection.
  Respect their terms. Prices and stock change, so report the date you checked.
- If the user names a store Betty doesn't know, still run the category or country query and verify availability.

## Must-know scoring facts (explain these to users)
- Score = 0.6 x nutrition (Nutri-Score, **original 2017 algorithm**, via Yuka's table) + 0.3 x additives + 0.1 x organic.
- **Only certified-organic products can exceed 90.** A perfect non-organic product is exactly 90.
- Any high-risk additive caps the score at 49, and Nutri-Score D/E caps it at 49.
- Open Food Facts' headline Nutri-Score now uses the **2023** algorithm. Betty uses the 2021 (original) field
  or recomputes it, so the numbers can differ from the OFF website. That's expected.
- "Unknown" halal means OFF has no ingredient list. Say so rather than guessing.

## Accuracy habits
1. Prefer barcodes. Names can match the wrong variant (regular vs low-sodium, US vs Canada).
2. If a product shows `capped`, flagged additives, or missing nutrition, mention it.
3. For a final shopping list, spot-check two or three items against the pack or label photo on the OFF page.
4. If OFF lacks nutrition for an item, the user can add it at world.openfoodfacts.org in a minute, and that helps everyone.
5. Never present halal-by-ingredients as certified. Never give medical advice.

## Output
Give a short table (score, band, product, brand, halal status, why), then offer the HTML report.
For a PDF, open the HTML report and print to PDF, or build one with a PDF skill using the `--json` output
(credit Open Food Facts; product photos are CC BY-SA).

Credits to show when sharing results: data from **Open Food Facts contributors (ODbL)**. Scoring method
described publicly by **Yuka**, with Nutri-Score by **Santé publique France**.
