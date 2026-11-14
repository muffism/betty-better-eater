"""The web app (docs/betty.js) must give exactly the same answers as the Python package."""
import json, os, shutil, subprocess, sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import build_web  # noqa: E402
from betty import additives, off  # noqa: E402
from betty.diet import DIETS, passes  # noqa: E402


def N(kcal, sugars=0, sat=0, sodium=0, fibre=0, protein=0, fvn=0, fat=None):
    n = {"energy-kcal_100g": kcal, "sugars_100g": sugars, "saturated-fat_100g": sat, "sodium_100g": sodium,
         "fiber_100g": fibre, "proteins_100g": protein,
         "fruits-vegetables-legumes-estimate-from-ingredients_100g": fvn}
    if fat is not None:
        n["fat_100g"] = fat
    return n


def P(code, ingr, nutr=None, **kw):
    p = dict(code=code, product_name=kw.pop("name", f"Product {code}"), ingredients_text=ingr,
             nutriments=nutr if nutr is not None else N(150, 2, 0.5, 0.1, 6, 10, 50))
    p.update(kw)
    return p


FIXTURES = [
    P("1", "organic chickpeas, water, sea salt", labels_tags=["en:organic", "en:orthodox-union-kosher"],
      ingredients_analysis_tags=["en:vegan", "en:palm-oil-free"]),
    P("2", "glucose syrup, sugar, gelatin, citric acid, carmine", N(340, 46, 0, 0.02, 0, 6),
      additives_tags=["en:e330", "en:e120"], ingredients_analysis_tags=["en:non-vegan"]),
    P("3", "sugar, pork gelatin, flavour"),
    P("4", "sugar, fish gelatin, citric acid", additives_tags=["en:e330"]),
    P("5", "pasteurized milk, bacterial culture, salt, microbial enzyme", N(400, 0, 21, 0.62, 0, 25, 0, 33),
      categories_tags=["en:dairies", "en:cheeses"], allergens_tags=["en:milk"],
      ingredients_analysis_tags=["en:vegetarian"]),
    P("6", "milk, salt, rennet", N(380, 0, 19, 0.7, 0, 24), categories_tags=["en:cheeses"], allergens_tags=["en:milk"]),
    P("7", "oats, sugar, natural flavour, vanilla extract", ingredients_analysis_tags=["en:vegan"]),
    P("8", "dates, vegetable glycerin", additives_tags=["en:e422"]),
    P("9", "dates, glycerin"),
    P("10", "sucre, farine de blé, crème, gélatine, présure", N(450, 30, 12, 0.3, 1, 5)),
    P("11", "water, red wine vinegar, salt"),
    P("12", "avocado, white vinegar, salt", ingredients_analysis_tags=["en:vegan"]),
    P("13", "chicken", name="Chicken breast", labels_tags=["en:halal"], categories_tags=["en:meats", "en:chickens"]),
    P("14", "chicken, salt", name="Chicken thighs", categories_tags=["en:poultries"]),
    P("15", "", N(200)),
    P("16", "rolled oats", N(380, 1, 1.2, 0, 10, 13), categories_tags=["en:rolled-oats"]),
    P("17", "gluten-free rolled oats", N(380, 1, 1.2, 0, 10, 13), labels_tags=["en:no-gluten"],
      traces_tags=["en:nuts"]),
    P("18", "milk, lactase enzyme", N(42, 4.8, 0.6, 0.04, 0, 3.4), labels_tags=["en:no-lactose"],
      allergens_tags=["en:milk"], categories_tags=["en:milks"]),
    P("19", "coconut milk, water, guar gum", N(20, 0, 2, 0.01, 0, 0.2), categories_tags=["en:plant-based-beverages",
                                                                                       "en:beverages"]),
    P("20", "orange juice", N(45, 9, 0, 0, 0.2, 0.7, 100), categories_tags=["en:beverages", "en:fruit-juices"]),
    P("21", "water", categories_tags=["en:beverages", "en:waters"]),
    P("22", "sugar, emulsifier (e471), colour (e102)", N(500, 50, 10, 0.2, 1, 4),
      additives_tags=["en:e471", "en:e102", "en:e441"]),
    P("23", "wheat flour, water, yeast, salt, enzymes", N(250, 3, 0.3, 0.45, 3, 9), allergens_tags=["en:gluten"]),
    P("24", "beef, salt, tallow", name="Beef jerky", categories_tags=["en:meats", "en:beef"]),
    P("25", "salmon, salt", name="Smoked salmon", categories_tags=["en:fishes"], allergens_tags=["en:fish"]),
    P("26", "shrimp, salt", allergens_tags=["en:crustaceans"]),
    P("27", "peanuts, sesame seeds, soy sauce (water, soybeans, wheat), mustard", allergens_tags=[
        "en:peanuts", "en:sesame-seeds", "en:soybeans", "en:gluten", "en:mustard"]),
    P("28", "almonds, honey, egg white", allergens_tags=["en:nuts", "en:eggs"], labels_tags=["en:vegetarian"]),
    P("29", "rum, raisins, sugar"),
    P("30", "olive oil", N(884, 0, 14, 0, 0, 0, 100, 100), categories_tags=["en:fats", "en:olive-oils"]),
    P("31", "oats", N(380), nutriscore={"2021": {"nutriscore_computed": 1, "score": -3}}),
    P("32", "mono- and diglycerides (vegetable origin), shellac, l-cysteine", additives_tags=["en:e904"]),
    P("33", "whey, casein, cocoa butter, chocolate", allergens_tags=["en:milk"]),
    P("34", "water, sugar, ethanol", additives_tags=["en:e1510"]),
    P("35", "sardines, olive oil, salt", N(208, 0, 2.5, 0.4, 0, 24, 15), categories_tags=["en:canned-fishes"]),
]


@pytest.fixture
def no_network(monkeypatch):
    monkeypatch.setattr(additives, "taxonomy", lambda: {})


def test_data_file_is_up_to_date(no_network):
    path = os.path.join(ROOT, "docs", "betty-data.js")
    text = open(path, encoding="utf-8").read()
    shipped = json.loads(text[text.index("{"):text.rindex("}") + 1])
    fresh = build_web.build(with_additives=False)
    for key, value in fresh.items():
        assert shipped[key] == json.loads(json.dumps(value)), f"docs/betty-data.js is stale ({key}): " \
                                                             "run python scripts/build_web.py"
    for code, level in additives.overrides().items():
        assert shipped["additives"].get(code) == level, code


@pytest.mark.skipif(not shutil.which("node"), reason="Node.js not installed")
def test_javascript_matches_python(no_network, tmp_path):
    data = build_web.build()                       # overrides-only additive levels, same as Python here
    (tmp_path / "data.json").write_text(json.dumps(data), encoding="utf-8")
    (tmp_path / "fixtures.json").write_text(json.dumps(FIXTURES), encoding="utf-8")
    runner = f"""
const fs = require("fs");
const data = JSON.parse(fs.readFileSync({json.dumps(str(tmp_path / 'data.json'))}, "utf8"));
const Betty = require({json.dumps(os.path.join(ROOT, 'docs', 'betty.js'))})(data);
const fx = JSON.parse(fs.readFileSync({json.dumps(str(tmp_path / 'fixtures.json'))}, "utf8"));
const out = fx.map((p) => {{
  const r = Betty.evaluate(p); const f = Betty.classify(p);
  const diets = Object.fromEntries(Object.keys(Betty.DIETS).map((d) => [d, Betty.passes(f, [d])]));
  return {{ r, diets, sim: Betty.similarCategories(p) }};
}});
process.stdout.write(JSON.stringify(out));
"""
    (tmp_path / "run.js").write_text(runner, encoding="utf-8")
    js = json.loads(subprocess.run(["node", str(tmp_path / "run.js")], capture_output=True, text=True,
                                   encoding="utf-8", check=True).stdout)
    from betty.cli import similar_categories
    from betty.diet import classify
    for p, got in zip(FIXTURES, js):
        want = off.evaluate(p)
        want = json.loads(json.dumps(want)) if want else None
        assert got["r"] == want, f"product {p['code']} differs"
        f = classify(p)
        assert got["diets"] == {d: passes(f, {d}) for d in DIETS}, f"diet filters differ for {p['code']}"
        assert got["sim"] == similar_categories(p)
