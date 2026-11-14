# Betty Better Eater 🥦

**Find healthier groceries at the store you actually shop at.**

Betty gives any food product a 0–100 health estimate in the spirit of the Yuka app, finds better
alternatives, and lets you browse a category at your own retailer and country, with diet filters for
**halal, no pork, no beef, vegetarian and vegan**. It runs on your own computer, uses free open data, and
works with or without an AI assistant.

> Betty is an independent hobby project. It is **not affiliated with Yuka** (or any retailer), and its
> numbers are **estimates**, not official Yuka scores. Please scan in the Yuka app or read the label when it matters.

---

## Quick start

**Easiest (no typing):**
- **Windows:** download this repo (green **Code** button, then **Download ZIP**), unzip, and double-click **`Betty (Windows).bat`**.
- **Mac:** double-click **`betty.command`** (first time: right-click, then **Open**).
- You need Python 3.10+ ([python.org](https://www.python.org/downloads/)). Betty installs itself the first time.

Betty then asks a few questions: what you want to do, your country and store, your diet, and how picky to be.

**Command line:**
```bash
pip install "git+https://github.com/muffism/betty-better-eater"
betty                                   # guided mode
betty score 0096619533602               # score a barcode
betty find "organic chickpeas" --country canada
betty better 0055991241031 --country canada --diet halal --band very-good
betty browse oats --country canada --store costco --min 90 --report oats.html
betty categories                        # category shortcuts (oats, chicken, frozen-vegetables, ...)
betty explain                           # how the score works
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
`--country` · `--store` · `--diet halal,no-pork,no-beef,halal-strict,vegetarian,vegan` · `--organic` ·
`--min` · `--band` · `--limit` · `--pages` (scan more products) · `--report list.html` (a printable list with photos;
print it to PDF from your browser) · `--json`

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

## About the diet filters (please read)
- `halal` passes products with a halal certification label, **or** non-meat products whose ingredients contain
  nothing known to be haram or doubtful (pork, alcohol, gelatin, rennet, carmine, L-cysteine, some emulsifiers...).
  Meat and poultry always need a certificate.
- `halal-strict` passes only products with a halal certification label.
- "Halal by ingredients" is **not** a certification or a religious ruling. Wine vinegar is flagged as *doubtful*
  so you can decide. When the ingredient list is missing, Betty says "unknown" rather than guessing.

## Your retailer
Betty uses Open Food Facts' store tags, which volunteers add. Big chains (Costco, Walmart, Tesco, Carrefour, Loblaws...)
are covered reasonably well and small shops less so. If a store search comes up short, search your country instead and
check the store's own website for availability. You can also add the store to products on Open Food Facts to help the next person.

## Offline / spreadsheet mode
```bash
python scripts/off_filter_dump.py --country canada --store costco --out costco_canada.tsv
```
This streams the full Open Food Facts dump (about 1.5 GB, never saved) and keeps just your slice.

## Using it with Claude (optional)
`skills/betty-better-eater/SKILL.md` is a ready-made Claude skill. Copy the folder into `~/.claude/skills/`
(Claude Code), or upload it as a skill in Claude, then ask things like *"What are the best halal snacks at Walmart Canada, 85 and up?"*

## Privacy
Betty doesn't collect anything. It only sends your search terms to Open Food Facts, and caches the answers in `~/.cache/betty`.

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

**Ideas we'd love help with:** phone barcode scanning (small web app), French/Spanish/Arabic/Urdu interface, price per score,
an optional 2023 Nutri-Score toggle, Yuka's separate water scale, and more halal certifier recognition.

## Licence
Code: MIT (see `LICENSE`). Data fetched from Open Food Facts stays under ODbL / CC BY-SA. See `NOTICE.md`.
This is not medical, nutritional or religious advice.
