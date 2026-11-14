/* Betty Better Eater: scoring and diet logic for the web app.
 * A line-by-line port of the Python package (betty/score.py, nutriscore.py, diet.py, off.py).
 * The word lists and tables come from betty-data.js, generated from the Python code, and
 * tests/test_web_parity.py checks that both give identical answers.
 * Browser: <script src="betty-data.js"></script><script src="betty.js"></script> -> window.Betty
 * Node:    require("./betty.js")(data)
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory;
  else root.Betty = factory(root.BETTY_DATA);
})(typeof self !== "undefined" ? self : this, function (D) {
  "use strict";
  const R = D.rules;

  // Python's \b and \w are Unicode-aware, JavaScript's are not ("blé", "crème"), so translate.
  const W = "[\\p{L}\\p{N}_]";
  const B = `(?:(?<=${W})(?!${W})|(?<!${W})(?=${W}))`;
  const rx = (src, g) => new RegExp(src.replace(/\\b/g, B).replace(/\\w/g, W), g ? "giu" : "iu");
  const has = (re, text) => !!text && re.test(text);
  const sub = (src, repl, text) => text.replace(rx(src, true), repl);
  const lowerSet = (a) => new Set((a || []).map((t) => String(t).toLowerCase()));
  const inter = (a, b) => [...a].some((x) => b.has(x));

  const RX = {};
  for (const k of ["PORK", "BEEF", "ALCOHOL", "ANIMAL_DERIVED", "MEAT", "FISH", "SHELLFISH", "GLUTEN_WORDS",
                   "OATS", "SUGARS", "DAIRY_WORDS", "GLYCERIN", "GF_WORD"]) RX[k] = rx(R[k]);
  const DOUBTFUL_WORDS = R.DOUBTFUL_WORDS.map(([s, label]) => [rx(s), label]);
  const CHECK_WORDS = R.CHECK_WORDS.map(([s, label]) => [rx(s), label]);
  const ANIMAL_E = new Set(R.ANIMAL_E), HARAM_E = new Set(R.HARAM_E);
  const GF_LABELS = new Set(R.GLUTEN_FREE_LABELS), LF_LABELS = new Set(R.LACTOSE_FREE_LABELS);

  // ------------------------------------------------------------ diet.classify
  function classify(p) {
    const ingr = [p.ingredients_text_en, p.ingredients_text].filter(Boolean).join(" ");
    const name = p.product_name_en || p.product_name || "";
    const cats = (p.categories_tags || []).join(" ");
    const labels = lowerSet(p.labels_tags), analysis = lowerSet(p.ingredients_analysis_tags);
    const allergens = lowerSet(p.allergens_tags), traces = lowerSet(p.traces_tags);
    const adds = new Set((p.additives_tags || []).map((a) => a.replace("en:", "")));
    const text = `${name} ${ingr} ${cats}`;
    const known = ingr.trim().length > 0;

    const ingrWoVinegar = sub(R.VINEGARS, "vinegar", ingr);
    const pork = has(RX.PORK, text) || cats.includes("en:pork") || allergens.has("en:pork");
    const beef = has(RX.BEEF, text) || cats.includes("en:beef") || allergens.has("en:beef");
    const alcohol = has(RX.ALCOHOL, ingrWoVinegar) || inter(adds, HARAM_E) || labels.has("en:contains-alcohol");
    const ingrOk = sub(R.DOUBTFUL_OK, " ", ingr);
    const doubtfulWhy = DOUBTFUL_WORDS.filter(([re]) => has(re, ingrOk)).map(([, l]) => l);
    if (allergens.has("en:gelatin") && !doubtfulWhy.includes("gelatin")) doubtfulWhy.push("gelatin");
    const plainGlycerin = has(RX.GLYCERIN, ingrOk) || !has(RX.GLYCERIN, ingr);
    for (const code of [...adds].filter((c) => c in R.DOUBTFUL_E).sort()) {
      const nm = R.DOUBTFUL_E[code];
      if (code === "e422" && !plainGlycerin) continue;
      if (!doubtfulWhy.some((d) => d.split(" (")[0] === nm.split(" (")[0])) doubtfulWhy.push(nm);
    }
    const doubtful = doubtfulWhy.length > 0;
    const checkWhy = CHECK_WORDS.filter(([re]) => has(re, ingr)).map(([, l]) => l);
    const ingrVeg = sub(R.VEG_RENNET_OK, " ", ingr);
    const animalDerived = has(RX.ANIMAL_DERIVED, sub(R.FISH_DERIVED_OK, " ", ingrVeg)) || inter(adds, ANIMAL_E);
    const anyAnimal = animalDerived || has(RX.ANIMAL_DERIVED, ingrVeg);
    const meat = has(RX.MEAT, text) || ["en:meats", "en:poultries", "en:chickens"].some((c) => cats.includes(c));
    const fish = has(RX.FISH, text) || allergens.has("en:fish") || cats.includes("en:fishes");
    const shellfish = has(RX.SHELLFISH, text) || allergens.has("en:crustaceans") || allergens.has("en:molluscs");

    const lab = [...labels];
    const vegan = (analysis.has("en:vegan") || lab.some((l) => l.includes("vegan") && !l.includes("non-vegan")))
      && !analysis.has("en:non-vegan") && !meat && !fish && !anyAnimal;
    const vegetarian = vegan || ((analysis.has("en:vegetarian") || lab.some((l) => l.includes("vegetarian") && !l.includes("non-")))
      && !analysis.has("en:non-vegetarian") && !meat && !fish && !anyAnimal);
    const halalCert = lab.some((l) => l.includes("halal"));
    const kosherCert = lab.some((l) => l.includes("kosher") || l.includes("pareve") || l.includes("parve"));
    let halal;
    if (halalCert && !pork && !alcohol) halal = "certified";
    else if (pork || alcohol) halal = "not-halal";
    else if (meat) halal = "not-certified-meat";
    else if (doubtful) halal = "doubtful";
    else if (!known) halal = "unknown";
    else halal = "ok-by-ingredients";

    const freeOf = (key) => known && !R.ALLERGEN[key].some((t) => allergens.has(t) || traces.has(t));
    const gfCert = inter(labels, GF_LABELS);
    const glutenFree = gfCert || (freeOf("gluten") && !has(RX.GLUTEN_WORDS, ingr)
      && (!has(RX.OATS, ingr) || has(RX.GF_WORD, ingr)));
    const ingrNoPlantMilk = sub(R.PLANT_MILKS, "", ingr);
    const dairyFree = vegan || (freeOf("milk") && !has(RX.DAIRY_WORDS, ingrNoPlantMilk));
    const lactoseFree = inter(labels, LF_LABELS) || dairyFree;
    const noAddedSugar = labels.has("en:no-added-sugar") || (known && !has(RX.SUGARS, ingr));
    const palmFree = analysis.has("en:palm-oil-free") || labels.has("en:no-palm-oil");
    const pescatarian = vegetarian || (known && !meat && !pork && !beef && !animalDerived);
    const free_of = {};
    for (const k of Object.keys(R.ALLERGEN)) free_of[k] = freeOf(k);
    return {
      known_ingredients: known, pork, beef, alcohol, doubtful, doubtful_why: doubtfulWhy, check_why: checkWhy,
      meat, fish, shellfish, halal, halal_certified: halalCert, kosher_certified: kosherCert, vegan, vegetarian,
      pescatarian, gluten_free: glutenFree, gluten_free_certified: gfCert, lactose_free: lactoseFree,
      dairy_free: dairyFree, no_added_sugar: noAddedSugar, palm_oil_free: palmFree, free_of,
    };
  }

  // Same tests as DIETS in betty/diet.py (labels and badges come from the data file).
  const TESTS = {
    "halal": (f) => f.halal === "certified" || f.halal === "ok-by-ingredients",
    "halal-strict": (f) => f.halal === "certified",
    "kosher": (f) => f.kosher_certified,
    "vegan": (f) => f.vegan,
    "vegetarian": (f) => f.vegetarian,
    "pescatarian": (f) => f.pescatarian,
    "no-pork": (f) => !f.pork,
    "no-beef": (f) => !f.beef,
    "no-alcohol": (f) => f.known_ingredients && !f.alcohol,
    "gluten-free": (f) => f.gluten_free,
    "gluten-free-strict": (f) => f.gluten_free_certified,
    "lactose-free": (f) => f.lactose_free,
    "dairy-free": (f) => f.dairy_free,
    "nut-free": (f) => f.free_of.nuts && f.free_of.peanuts,
    "peanut-free": (f) => f.free_of.peanuts,
    "egg-free": (f) => f.free_of.eggs,
    "soy-free": (f) => f.free_of.soy,
    "sesame-free": (f) => f.free_of.sesame,
    "fish-free": (f) => f.free_of.fish && !f.fish,
    "shellfish-free": (f) => f.free_of.shellfish && !f.shellfish,
    "mustard-free": (f) => f.free_of.mustard,
    "no-added-sugar": (f) => f.no_added_sugar,
    "palm-oil-free": (f) => f.palm_oil_free,
  };
  const DIETS = {};
  for (const [key, label, badge] of D.diets) {
    if (!TESTS[key]) throw new Error("betty.js has no test for diet " + key);
    DIETS[key] = { label, badge, test: TESTS[key] };
  }
  const passes = (flags, diet) => [...diet].every((d) => DIETS[d].test(flags));

  function badges(flags) {
    const out = [];
    if (flags.halal === "certified") out.push("Halal certified");
    else if (flags.halal === "ok-by-ingredients") out.push("Halal (ingredients)");
    for (const key of ["kosher", "vegan", "vegetarian", "gluten-free", "dairy-free", "lactose-free",
                       "nut-free", "egg-free", "soy-free", "no-added-sugar"]) {
      let { test, badge } = DIETS[key];
      if (!badge || !test(flags)) continue;
      if (key === "vegetarian" && flags.vegan) continue;
      if (key === "lactose-free" && flags.dairy_free) continue;
      if (key === "gluten-free" && flags.gluten_free_certified) badge = "Gluten-free (labelled)";
      out.push(badge);
    }
    return out;
  }

  function warnings(flags) {
    const w = [];
    if (flags.halal === "not-halal") {
      const why = [["pork", flags.pork], ["alcohol", flags.alcohol]].filter(([, on]) => on).map(([x]) => x);
      w.push("not halal" + (why.length ? ` (${why.join(", ")})` : ""));
    } else if (flags.halal === "doubtful") w.push("halal doubtful: " + flags.doubtful_why.join(", "));
    else if (flags.halal === "not-certified-meat") w.push("meat not halal-certified");
    if ((flags.halal === "ok-by-ingredients" || flags.halal === "doubtful") && flags.check_why.length)
      w.push("halal: check " + flags.check_why.join(" & "));
    if (!flags.known_ingredients) w.push("no ingredient list: additives unchecked");
    return w;
  }

  // ------------------------------------------------------------ nutriscore.points (2017)
  const steps = (v, ts) => ts.filter((t) => v > t).length;
  const range = (k) => Array.from({ length: 10 }, (_, i) => k * (i + 1));
  function nsPoints(n, { beverage = false, cheese = false, added_fat = false } = {}) {
    const kj = n.kcal * 4.184;
    let neg;
    if (beverage) {
      neg = steps(kj, [0, 30, 60, 90, 120, 150, 180, 210, 240, 270]);
      neg += steps(n.sugars, [0, 1.5, 3, 4.5, 6, 7.5, 9, 10.5, 12, 13.5]);
    } else {
      neg = steps(kj, range(335));
      neg += steps(n.sugars, [4.5, 9, 13.5, 18, 22.5, 27, 31, 36, 40, 45]);
    }
    if (added_fat && n.fat) neg += steps(n.sat_fat / n.fat * 100, [10, 16, 22, 28, 34, 40, 46, 52, 58, 64]);
    else neg += steps(n.sat_fat, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
    neg += steps(n.sodium_mg, range(90));
    const fv = beverage ? (n.fvn_pct > 80 ? 10 : n.fvn_pct > 60 ? 4 : n.fvn_pct > 40 ? 2 : 0)
                        : (n.fvn_pct > 80 ? 5 : n.fvn_pct > 60 ? 2 : n.fvn_pct > 40 ? 1 : 0);
    const fi = steps(n.fibre, [0.9, 1.9, 2.8, 3.7, 4.7]);
    const pr = steps(n.protein, [1.6, 3.2, 4.8, 6.4, 8.0]);
    if (neg >= 11 && fv < (beverage ? 10 : 5) && !cheese) return neg - fv - fi;
    return neg - fv - fi - pr;
  }

  // ------------------------------------------------------------ score.estimate
  const pyRound = (x) => (Math.abs(x % 1) === 0.5 ? 2 * Math.round(x / 2) : Math.round(x)); // Python rounds half to even
  function band(s) {
    for (const [name, floor] of D.bands) if (s >= floor) return name;
    return "Very bad";
  }
  function nutritionRating(pts, beverage) {
    if (beverage) return pts <= -4 ? 80 : (D.liquid[String(pts)] ?? 0);
    if (pts <= -2) return 100;
    return pts >= 19 ? 0 : D.solid[String(pts)];
  }
  const norm = (c) => c.toLowerCase().replace("en:", "").replace(/ /g, "").replace(/-/g, "");
  function risk(code) {
    const c = norm(code);
    const base = c[0] === "e" ? c.replace(/[a-z]+$/, "") : c;
    return D.additives[c] || D.additives[base] || "unknown";
  }
  function estimate(pts, organic, risks, beverage) {
    const vals = Object.values(risks);
    const n = nutritionRating(pts, beverage);
    let a = 100 - vals.reduce((s, r) => s + (D.additive_cost[r] ?? 10), 0);
    a = Math.max(0, a);
    let s = 0.6 * n + 0.3 * a + 0.1 * (organic ? 100 : 0), cap = null;
    if (vals.includes("high")) { s = Math.min(s, 49); cap = "high-risk additive"; }
    if (!beverage && pts >= 11) { s = Math.min(s, 49); cap = cap || "Nutri-Score D/E"; }
    const flagged = Object.keys(risks).filter((k) => risks[k] !== "risk-free").sort();
    return { score: pyRound(s), nutrition_rating: n, additive_rating: a, organic, capped: cap, flagged_additives: flagged };
  }

  // ------------------------------------------------------------ off.evaluate
  const BEV = new Set(D.beverage_cats), NOT_BEV = new Set(D.not_beverage);
  const isOrganic = (p) => D.organic_labels.some((t) => (p.labels_tags || []).includes(t));
  function toNutrition(p) {
    const n = p.nutriments || {};
    if (!("energy-kcal_100g" in n) && !("energy_100g" in n)) return null;
    const num = (k) => Number(n[k]) || 0;
    return {
      kcal: num("energy-kcal_100g") || num("energy_100g") / 4.184, sugars: num("sugars_100g"),
      sat_fat: num("saturated-fat_100g"), sodium_mg: num("sodium_100g") * 1000, fibre: num("fiber_100g"),
      protein: num("proteins_100g"),
      fvn_pct: num("fruits-vegetables-legumes-estimate-from-ingredients_100g")
        || num("fruits-vegetables-nuts-estimate-from-ingredients_100g"),
      fat: n.fat_100g == null ? null : Number(n.fat_100g),
    };
  }
  function evaluate(p) {
    const cats = new Set(p.categories_tags || []);
    const beverage = inter(cats, BEV) && !inter(cats, NOT_BEV);
    if (cats.has("en:waters")) return null;
    const ns = (p.nutriscore || {})["2021"] || {};
    let pts = ns.nutriscore_computed && ns.score != null ? ns.score : null;
    let source = "Open Food Facts (Nutri-Score 2021 field = original algorithm)";
    if (pts == null) {
      const nut = toNutrition(p);
      if (!nut) return null;
      pts = nsPoints(nut, { beverage, cheese: cats.has("en:cheeses"), added_fat: cats.has("en:fats") });
      source = "computed by Betty from Open Food Facts nutrients";
    }
    pts = Math.trunc(Number(pts));
    const risks = {};
    for (const c of p.additives_tags || []) risks[norm(c)] = risk(c);
    const est = estimate(pts, isOrganic(p), risks, beverage);
    const diet = classify(p);
    return {
      code: p.code ?? null, name: p.product_name_en || (p.product_name ?? null), brands: p.brands ?? null,
      quantity: p.quantity ?? null, stores: p.stores ?? null,
      image: p.image_front_url || (p.image_front_small_url ?? null),
      url: `https://world.openfoodfacts.org/product/${p.code}`, score: est.score, label: band(est.score),
      nutriscore_points: pts, nutrition_rating: est.nutrition_rating, additive_rating: est.additive_rating,
      organic: est.organic, capped: est.capped, flagged_additives: est.flagged_additives, beverage,
      nutrition_source: source, diet, fits: badges(diet), warnings: warnings(diet), categories: p.categories_tags || [],
    };
  }

  const GENERIC = new Set(D.generic);
  function similarCategories(p) {
    const cats = p.categories_hierarchy || p.categories_tags || [];
    const out = [];
    for (const c of [...cats].reverse()) {
      if (!/^[a-z]{2}:[a-z0-9-]+$/.test(c)) continue;      // e.g. "fr:Nutella": a brand typed as a category
      if (!GENERIC.has(c) && !out.includes(c)) out.push(c);
    }
    return out;
  }
  function resolveCategory(name) {
    const n = name.trim().toLowerCase().replace(/ /g, "-");
    if (n.includes(":")) return n;
    if (D.shortcuts[n]) return D.shortcuts[n];
    if (n.endsWith("s") && D.shortcuts[n.slice(0, -1)]) return D.shortcuts[n.slice(0, -1)];
    return "en:" + n;
  }
  function bandFloor(name) {
    const key = name.toLowerCase().replace(/[-_]/g, " ").trim();
    const hit = D.bands.find(([n]) => n.toLowerCase() === key);
    if (!hit) throw new Error("Unknown band " + name);
    return hit[1];
  }

  return { classify, passes, badges, warnings, nsPoints, estimate, evaluate, band, bandFloor, risk,
           similarCategories, resolveCategory, DIETS, data: D };
});
