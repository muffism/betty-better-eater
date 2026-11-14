"""Diet & free-from filters, and the "Fits:" badges shown on each product.

Data comes from Open Food Facts (crowd-sourced): labels, allergens, "may contain"
traces, ingredient analysis and the ingredient text. Rules of thumb:
  * Religious diets: halal/kosher *certified* = a certifier label on the pack.
    "Halal (by ingredients)" only means nothing known to be haram or doubtful was
    found. It is NOT a certification or a religious ruling. Kosher has no
    "by ingredients" version because kashrut can't be judged from a list.
  * Free-from filters are CAUTIOUS: no ingredient data -> excluded; a "may contain"
    warning counts as containing. Still, for a serious allergy ALWAYS read the pack.
"""
import re

# ---------------------------------------------------------------- word lists
PORK = r"\b(pork|porc|bacon|ham|jambon|lard|saindoux|prosciutto|pancetta|chorizo|salami|pepperoni|pig|swine)\b"
BEEF = r"\b(beef|boeuf|bœuf|veal|veau|brisket|bison)\b"
ALCOHOL = r"\b(wine|vin|beer|bière|rum|rhum|brandy|cognac|whisk(e)?y|vodka|liqueur|alcohol|alcool|ethanol|ethyl alcohol|mirin|sake)\b"
DOUBTFUL = r"\b(gelatin[e]?|gélatine|rennet|présure|carmine|cochineal|l-cysteine|shellac|mono- and diglycerides)\b"
MEAT = r"\b(chicken|poulet|turkey|dinde|lamb|agneau|mutton|goat|duck|canard|venison|meat|viande|beef|pork|veal)\b"
FISH = r"\b(fish|poisson|salmon|saumon|tuna|thon|sardine|cod|morue|tilapia|trout|mackerel|anchov\w*|herring|pollock|haddock)\b"
SHELLFISH = r"\b(shrimp|prawn|crab|lobster|crayfish|clam|mussel|oyster|scallop|squid|octopus|crevette|homard)\b"
GLUTEN_WORDS = r"\b(wheat|blé|barley|orge|rye|seigle|spelt|épeautre|malt|triticale|kamut|semolina|durum|farro|bulgur|couscous|seitan)\b"
OATS = r"\b(oats?|oat flour|avoine)\b"
SUGARS = r"\b(sugar|sucre|syrup|sirop|dextrose|glucose|fructose|sucrose|maltose|honey|miel|molasses|agave|cane juice|maltodextrin)\b"
DAIRY_WORDS = r"\b(milk|lait|cream|crème|butter|beurre|cheese|fromage|whey|lactosérum|casein|caséine|yogurt|yaourt|lactose|ghee)\b"
PLANT_MILKS = r"\b(coconut|almond|oat|soy|soya|rice|cashew|cocoa|peanut|shea|nut) (milk|butter|cream)\b"

DOUBTFUL_E = {"e120", "e441", "e542", "e904", "e920", "e921", "e471", "e472a", "e472b", "e472c",
              "e472e", "e481", "e482", "e491"}
HARAM_E = {"e1510"}

ALLERGEN = {  # Betty name -> Open Food Facts allergen tag(s)
    "gluten": ["en:gluten"], "milk": ["en:milk"], "eggs": ["en:eggs"], "nuts": ["en:nuts"],
    "peanuts": ["en:peanuts"], "soy": ["en:soybeans"], "sesame": ["en:sesame-seeds"],
    "fish": ["en:fish"], "shellfish": ["en:crustaceans", "en:molluscs"], "mustard": ["en:mustard"],
    "celery": ["en:celery"], "sulphites": ["en:sulphur-dioxide-and-sulphites"], "lupin": ["en:lupin"],
}
GLUTEN_FREE_LABELS = {"en:no-gluten", "en:certified-gluten-free", "en:gfco-gluten-free", "en:dzg-gluten-free",
                      "en:beyond-celiac-gluten-free", "en:canadian-celiac-association-gluten-free",
                      "en:free-from-dairy-and-gluten", "en:gluten-free"}
LACTOSE_FREE_LABELS = {"en:no-lactose", "en:naturally-lactose-free", "en:lactose-free"}


def _has(rx, text):
    return bool(text) and re.search(rx, text, flags=re.I) is not None


def _tags(tags):
    return {t.lower() for t in (tags or [])}


# ---------------------------------------------------------------- classify
def classify(p: dict) -> dict:
    ingr = " ".join(filter(None, [p.get("ingredients_text_en"), p.get("ingredients_text")]))
    name = p.get("product_name_en") or p.get("product_name") or ""
    cats = " ".join(p.get("categories_tags") or [])
    labels = _tags(p.get("labels_tags"))
    analysis = _tags(p.get("ingredients_analysis_tags"))
    allergens = _tags(p.get("allergens_tags"))
    traces = _tags(p.get("traces_tags"))
    adds = {a.replace("en:", "") for a in p.get("additives_tags") or []}
    text = f"{name} {ingr} {cats}"
    known = bool(ingr.strip())

    # wine vinegar: halal for most scholars -> "doubtful" (user decides), not alcohol
    ingr_wo_vinegar = re.sub(r"\b(wine|sherry|malt|cider) vinegar\b", "vinegar", ingr, flags=re.I)
    pork = _has(PORK, text) or "en:pork" in cats or "en:pork" in allergens
    beef = _has(BEEF, text) or "en:beef" in cats or "en:beef" in allergens
    alcohol = _has(ALCOHOL, ingr_wo_vinegar) or bool(adds & HARAM_E) or "en:contains-alcohol" in labels
    doubtful = (_has(DOUBTFUL, ingr) or bool(adds & DOUBTFUL_E) or _has(r"\bwine vinegar\b", ingr)
                or "en:gelatin" in allergens)
    meat = _has(MEAT, text) or any(c in cats for c in ("en:meats", "en:poultries", "en:chickens"))
    fish = _has(FISH, text) or "en:fish" in allergens or "en:fishes" in cats
    shellfish = _has(SHELLFISH, text) or bool({"en:crustaceans", "en:molluscs"} & allergens)

    vegan = (("en:vegan" in analysis or any("vegan" in l and "non-vegan" not in l for l in labels))
             and "en:non-vegan" not in analysis and not meat and not fish)
    vegetarian = vegan or (("en:vegetarian" in analysis
                            or any("vegetarian" in l and "non-" not in l for l in labels))
                           and "en:non-vegetarian" not in analysis and not meat and not fish)

    halal_cert = any("halal" in l for l in labels)
    kosher_cert = any("kosher" in l or "pareve" in l or "parve" in l for l in labels)
    if halal_cert and not pork and not alcohol:
        halal = "certified"
    elif pork or alcohol:
        halal = "not-halal"
    elif meat:
        halal = "not-certified-meat"
    elif doubtful:
        halal = "doubtful"
    elif not known:
        halal = "unknown"
    else:
        halal = "ok-by-ingredients"

    def free_of(key):
        """True only if we have ingredient data and neither allergens nor 'may contain' mention it."""
        if not known:
            return False
        tags = set(ALLERGEN[key])
        return not (tags & allergens) and not (tags & traces)

    gf_cert = bool(labels & GLUTEN_FREE_LABELS)
    gluten_free = gf_cert or (free_of("gluten") and not _has(GLUTEN_WORDS, ingr)
                              and (not _has(OATS, ingr) or _has(r"gluten[- ]free", ingr)))
    ingr_no_plant_milk = re.sub(PLANT_MILKS, "", ingr, flags=re.I)
    dairy_free = vegan or (free_of("milk") and not _has(DAIRY_WORDS, ingr_no_plant_milk))
    lactose_free = bool(labels & LACTOSE_FREE_LABELS) or dairy_free
    no_added_sugar = "en:no-added-sugar" in labels or (known and not _has(SUGARS, ingr))
    palm_free = "en:palm-oil-free" in analysis or "en:no-palm-oil" in labels
    pescatarian = vegetarian or (known and not meat and not pork and not beef)

    return dict(
        known_ingredients=known, pork=pork, beef=beef, alcohol=alcohol, doubtful=doubtful, meat=meat,
        fish=fish, shellfish=shellfish, halal=halal, halal_certified=halal_cert, kosher_certified=kosher_cert,
        vegan=vegan, vegetarian=vegetarian, pescatarian=pescatarian, gluten_free=gluten_free,
        gluten_free_certified=gf_cert, lactose_free=lactose_free, dairy_free=dairy_free,
        no_added_sugar=no_added_sugar, palm_oil_free=palm_free,
        free_of={k: free_of(k) for k in ALLERGEN},
    )


# ---------------------------------------------------------------- diets
# key: (menu label, test(flags) -> bool, badge shown on a product or None)
DIETS = {
    "halal":              ("Halal: certified, or non-meat with no haram/doubtful ingredients",
                           lambda f: f["halal"] in ("certified", "ok-by-ingredients"), None),
    "halal-strict":       ("Halal: certified label only", lambda f: f["halal"] == "certified", None),
    "kosher":             ("Kosher: certified label only", lambda f: f["kosher_certified"], "Kosher"),
    "vegan":              ("Vegan", lambda f: f["vegan"], "Vegan"),
    "vegetarian":         ("Vegetarian", lambda f: f["vegetarian"], "Vegetarian"),
    "pescatarian":        ("Pescatarian (no meat; fish ok)", lambda f: f["pescatarian"], None),
    "no-pork":            ("No pork", lambda f: not f["pork"], None),
    "no-beef":            ("No beef", lambda f: not f["beef"], None),
    "no-alcohol":         ("No alcohol", lambda f: f["known_ingredients"] and not f["alcohol"], None),
    "gluten-free":        ("Gluten-free (label, or no gluten in ingredients / 'may contain')",
                           lambda f: f["gluten_free"], "Gluten-free"),
    "gluten-free-strict": ("Gluten-free: labelled gluten-free on the pack only (best for celiac)",
                           lambda f: f["gluten_free_certified"], None),
    "lactose-free":       ("Lactose-free", lambda f: f["lactose_free"], "Lactose-free"),
    "dairy-free":         ("Dairy-free", lambda f: f["dairy_free"], "Dairy-free"),
    "nut-free":           ("Tree-nut & peanut free",
                           lambda f: f["free_of"]["nuts"] and f["free_of"]["peanuts"], "Nut-free"),
    "peanut-free":        ("Peanut-free", lambda f: f["free_of"]["peanuts"], None),
    "egg-free":           ("Egg-free", lambda f: f["free_of"]["eggs"], "Egg-free"),
    "soy-free":           ("Soy-free", lambda f: f["free_of"]["soy"], "Soy-free"),
    "sesame-free":        ("Sesame-free", lambda f: f["free_of"]["sesame"], None),
    "fish-free":          ("Fish-free", lambda f: f["free_of"]["fish"] and not f["fish"], None),
    "shellfish-free":     ("Shellfish-free", lambda f: f["free_of"]["shellfish"] and not f["shellfish"], None),
    "mustard-free":       ("Mustard-free", lambda f: f["free_of"]["mustard"], None),
    "no-added-sugar":     ("No added sugar", lambda f: f["no_added_sugar"], "No added sugar"),
    "palm-oil-free":      ("Palm-oil free", lambda f: f["palm_oil_free"], None),
}


def passes(flags: dict, diet: set) -> bool:
    return all(DIETS[d][1](flags) for d in diet)


def badges(flags: dict) -> list:
    """Only the diets this product actually fits (shown as 'Fits: ...')."""
    out = []
    if flags["halal"] == "certified":
        out.append("Halal certified")
    elif flags["halal"] == "ok-by-ingredients":
        out.append("Halal (ingredients)")
    for key in ("kosher", "vegan", "vegetarian", "gluten-free", "dairy-free", "lactose-free",
                "nut-free", "egg-free", "soy-free", "no-added-sugar"):
        _, test, badge = DIETS[key]
        if not badge or not test(flags):
            continue
        if key == "vegetarian" and flags["vegan"]:
            continue                       # vegan already implies it
        if key == "lactose-free" and flags["dairy_free"]:
            continue                       # dairy-free already implies it
        if key == "gluten-free" and flags["gluten_free_certified"]:
            badge = "Gluten-free (labelled)"
        out.append(badge)
    return out


def warnings(flags: dict) -> list:
    """Short heads-ups, shown only when they apply."""
    w = []
    if flags["halal"] == "not-halal":
        w.append("not halal")
    elif flags["halal"] == "doubtful":
        w.append("halal: doubtful ingredient")
    elif flags["halal"] == "not-certified-meat":
        w.append("meat not halal-certified")
    if not flags["known_ingredients"]:
        w.append("no ingredient list yet")
    return w
