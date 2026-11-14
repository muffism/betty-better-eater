# Betty Better Eater 🥦

**Find healthier groceries at the store you actually shop at.**

Betty gives any food product a 0–100 health estimate in the spirit of the Yuka app, finds better
alternatives, and lets you browse a category at your own retailer and country, with **diet and allergy
filters** (halal, kosher, vegan, vegetarian, gluten-free, lactose-free, nut-free and more). Every product shows
only the diets it actually fits. It runs on your own computer, uses free open data, and works with or without an
AI assistant.

> ⚠️ **Guide only.** Betty is a helpful guide, not a guarantee. Always read the label yourself to confirm ingredients, allergens and certifications. What you buy and eat is your own decision and at your own discretion. Not medical, allergy or religious advice.

> Betty is an independent hobby project. It is **not affiliated with Yuka** (or any retailer), and its
> numbers are **estimates**, not official Yuka scores. Please scan in the Yuka app or read the label when it matters.

---

## Quick start

**Easiest: open the web app** 👉 **https://muffism.github.io/betty-better-eater/**
Works on phones and computers, nothing to install, no sign-up. On Android/Chrome you can scan barcodes with your camera.
It runs entirely in your browser and talks only to Open Food Facts.

**On your computer (no typing):**
- **Windows:** download this repo (green **Code** button, then **Download ZIP**), unzip, and double-click **`Betty (Windows).bat`**.
- **Mac:** double-click **`betty.command`** (first time: right-click, then **Open**).
- You need Python 3.10+ ([python.org](https://www.python.org/downloads/)). Betty installs itself the first time.

Betty then asks a few questions: what you want to do, your country and store, your diet, and how picky to be.

**The first time, Betty asks one more:** *"Do you want to download the data? It will be around 1.5 GB."*
- **Yes (fast):** Betty downloads Open Food Facts once (10–30 minutes), keeps only the products sold in your
  country (a ~100–300 MB file), and from then on every search is **instant** and works without internet.
- **No (online):** nothing to download, but each search takes 10–40 seconds, because Open Food Facts asks apps
  to go slowly. You can switch any time with `betty download`.

**Command line:**
```bash
pip install "git+https://github.com/muffism/betty-better-eater"
betty                                   # guided mode
betty score 0096619533602               # score a barcode
betty find "organic chickpeas" --country canada
betty better 0055991241031 --country canada --diet halal --band very-good
betty browse oats --country canada --store costco --min 90 --report oats.html
betty find "granola" --country canada --diet gluten-free,nut-free,vegan
betty categories                        # category shortcuts (oats, chicken, frozen-vegetables, ...)
betty diets                             # every diet & allergy filter
betty explain                           # how the score works
betty download --country canada         # fast offline mode (refresh monthly with the same command)
betty download --status                 # what's downloaded;  --remove  deletes it and goes back online
```

### Your own bar: a number, a band, or both
| Band | Score |
|---|---|
| Excellent | 90–100 |
| Very good | 75–89 |
| Good | 50–74 |
| Bad | 25–49 |
| Very bad | 0–24 |

Use `--band very-good`, or your own cut-off with `--min 85`. If you give both, the stricter one wins.

### Options that work everywhere
`--country` · `--store` · `--diet` (see below) · `--organic` ·
`--min` · `--band` · `--limit` · `--pages` (scan more products) · `--report list.html` (a printable list with photos;
print it to PDF from your browser) · `--json` · `--online` (skip the offline data for one search)

---

## How the estimate works

Yuka explains its method publicly ([help.yuka.io](https://help.yuka.io/l/en/article/ijzgfvi1jq)). Betty re-implements that description:

| Part | Weight | Source |
|---|---|---|
| Nutrition | 60% | Nutri-Score, **original (2017) algorithm**, converted with Yuka's published table |
| Additives | 30% | Risk levels: Open Food Facts/EFSA data plus a small curated list. One high-risk additive caps the product at 49 |
| Organic | 10% | Bonus for an official organic label |

Things worth knowing:
- **Only certified-organic products can go above 90.** A perfect non-organic food is exactly 90.
- Nutri-Score D or E means the score can't exceed 49.
- Open Food Facts' website now shows the **2023** Nutri-Score. Betty deliberately uses the original algorithm, because that's
  what Yuka says it uses, so the letters can differ.
- How Yuka weighs low- and moderate-risk additives isn't public, so Betty approximates it and **flags** those additives for you to check.

**How close is it?** Betty reproduced five real Yuka scores that people posted online:
an organic lentil soup (100), organic rolled oats (100), clean non-organic foods (90), organic milk (85) and
organic coconut water (81). It's encouraging, but five checks aren't proof. Please send corrections.

## Diet & allergy filters
Combine any of these with commas, e.g. `--diet halal,gluten-free,nut-free` (or pick numbers in guided mode):

| Group | Options |
|---|---|
| Religious | `halal`, `halal-strict` (certified only), `kosher` (certified only) |
| Lifestyle | `vegan`, `vegetarian`, `pescatarian`, `no-pork`, `no-beef`, `no-alcohol` |
| Free-from | `gluten-free`, `gluten-free-strict` (labelled gluten-free on the pack, best for celiac), `lactose-free`, `dairy-free`, `nut-free`, `peanut-free`, `egg-free`, `soy-free`, `sesame-free`, `fish-free`, `shellfish-free`, `mustard-free` |
| Other | `no-added-sugar`, `palm-oil-free` |

Each product lists **only the diets it fits**, e.g. `Fits: Halal (ingredients) · Kosher · Vegan · Gluten-free`.

How careful is it?
- **No ingredient list = additives unchecked**, so that product's score may be too high; Betty says so on the product.
- **Free-from filters are cautious.** Products with no ingredient list are left out, and "may contain" warnings count
  as containing. Plain oats are not called gluten-free unless labelled. Crowd-sourced data can still be wrong, so
  **with a real allergy, always read the pack.**
- `halal` passes products with a halal certification label, **or** non-meat products whose ingredients contain nothing
  known to be haram or doubtful. Meat and poultry always need a certificate. "Halal (ingredients)" is **not** a
  certification or a religious ruling.

  | Ingredient | Betty says |
|---|---|
  | Pork in any form (incl. pork gelatin, lard), alcohol, E1510 | **Not halal** |
  | Gelatin (E441), collagen, rennet, enzymes of unstated source, carmine (E120), L-cysteine (E920), shellac (E904), bone phosphate (E542), mono- & diglycerides (E471/E472), glycerin (E422), tallow/animal fat, wine vinegar | **Doubtful**: left out by the `halal` filter and named on the product, e.g. `halal doubtful: gelatin` |
  | The same with a stated halal-friendly source: fish or halal gelatin, microbial/vegetable rennet or enzymes, vegetable glycerin, mono- & diglycerides of vegetable origin | Fine |
  | Flavourings, vanilla extract | A "check" note only (most scholars are lenient); doesn't fail the filter |
  | Anything with a halal certification label (and no pork/alcohol listed) | **Halal certified**: the certifier's word wins |

  Vegetarian, vegan and pescatarian also refuse gelatin, collagen, animal rennet, carmine and animal fat (fish gelatin is fine for pescatarians).
- `kosher` needs a kosher certification label (OU, Star-K, COR, MK, Kosher Parve...). Kashrut can't be judged from an
  ingredient list, so there's no "by ingredients" version.

## Your retailer
Betty uses Open Food Facts' store tags, which volunteers add. Big chains (Costco, Walmart, Tesco, Carrefour, Loblaws...)
are covered reasonably well and small shops less so. If a store search comes up short, search your country instead and
check the store's own website for availability. You can also add the store to products on Open Food Facts to help the next person.

## Fast offline mode
`betty download --country canada` streams the full Open Food Facts export once (about 1.5 GB, never saved to disk)
and keeps only the products sold in your country, in `~/.cache/betty/products-<country>.db`. After that:
- `find`, `browse` and `better` search that file instantly and scan up to 3,000 products per search, not 100.
- Searches for another country (`--country france`) and `--online` still go to the live site.
- The export leaves the store blank for most products, even though the live site has it. So the first time you
  search a store (`--store costco`), Betty fetches that store's product list online once (about 40 seconds for
  Costco Canada) and keeps it for 30 days. After that, store searches are instant too.
- `betty score <barcode>` still checks online first (one quick lookup gives the freshest data) and uses the file if
  you're offline.
- The export doesn't include Open Food Facts' own Nutri-Score field, so Betty computes it from the nutrients, and
  uses the measured fruit/vegetable share instead of the estimate. A few products can differ by a few points from
  the online score; `betty score <barcode>` shows the online one.
- It is a snapshot: refresh it monthly with `betty download` (Betty reminds you after 30 days).

The export is the way Open Food Facts recommends for heavy use, so it's also kinder to their servers.

**Spreadsheet instead?** `python scripts/off_filter_dump.py --country canada --store costco --out costco_canada.tsv`
saves your slice as a TSV you can open in Excel (filtered, not scored).

## Using it with Claude (optional)
`skills/betty-better-eater/SKILL.md` is a ready-made Claude skill. Copy the folder into `~/.claude/skills/`
(Claude Code), or upload it as a skill in Claude, then ask things like *"What are the best halal snacks at Walmart Canada, 85 and up?"*

## Privacy
Betty doesn't collect anything. It only sends your search terms to Open Food Facts (in offline mode, not even
that). The command line keeps its cache, settings and offline data in `~/.cache/betty`; the web app keeps your
choices in your own browser only.

## Credits, with gratitude 🙏
Betty is mostly other people's good work, glued together:
- **[Open Food Facts](https://world.openfoodfacts.org)** and its thousands of volunteer contributors: every product, photo,
  ingredient list and nutrient value comes from them. Data under the [Open Database License](https://opendatacommons.org/licenses/odbl/1-0/),
  photos under CC BY-SA. If Betty helps you, please [add a product](https://world.openfoodfacts.org/contribute) or [donate to them](https://world.openfoodfacts.org/donate-to-open-food-facts).
- **[Yuka](https://yuka.io)**, for openly explaining how its scores work, including the Nutri-Score correspondence table. Betty is
  a tribute to that transparency, not a replacement. Their app is excellent, so please use it.
- **Santé publique France** and the Nutri-Score scientific committee, for the Nutri-Score.
- **EFSA**, whose additive evaluations (via Open Food Facts' taxonomy) inform the risk levels.
- **USDA FoodData Central**, for reference nutrient values used while testing.
- The shoppers who share their Yuka scans on blogs, Lemon8, TikTok and Benable, which made it possible to check the maths.
- Built with help from Claude (Anthropic).

## Contributing
Corrections are very welcome, especially to `betty/data/additive_overrides.json` (please cite a source), category shortcuts,
translations, and real Yuka scans that disagree with Betty (`tests/test_score.py`). Run `pytest` before sending a PR.

The Python package is the single source of truth. The web app (`docs/`) uses the same rules: after changing word lists,
diets, shortcuts or additive levels, run `python scripts/build_web.py`. `tests/test_web_parity.py` checks that the web
app and the command line give identical answers (it needs Node.js).

**Ideas we'd love help with:** barcode scanning on iPhone (Safari has no built-in barcode reader), French/Spanish/Arabic/Urdu interface, price per score,
an optional 2023 Nutri-Score toggle, Yuka's separate water scale, and more halal certifier recognition.

## Licence & responsibility
Code: MIT (see `LICENSE`). Data fetched from Open Food Facts stays under ODbL / CC BY-SA. See `NOTICE.md`.

> ⚠️ **Guide only.** Betty is a helpful guide, not a guarantee. Always read the label yourself to confirm ingredients, allergens and certifications. What you buy and eat is your own decision and at your own discretion. Not medical, allergy or religious advice.
