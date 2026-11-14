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
# Halal "doubtful" (mashbooh): could be animal or alcohol derived. Fails the halal filter
# unless the pack is halal-certified. Each entry: (regex, name shown to the user).
DOUBTFUL_WORDS = [
    (r"\b(gelatin[e]?|gélatine)\b", "gelatin"),
    (r"\b(collagen|collagène)\b", "collagen"),
    (r"\b(rennet|présure)\b", "rennet"),
    (r"\benzymes?\b", "enzymes (source not stated)"),
    (r"\b(carmine|cochineal|carminic acid)\b", "carmine"),
    (r"\bl-cysteine\b", "L-cysteine"),
    (r"\bshellac\b", "shellac"),
    (r"\bmono-? ?(and|&) ?di-?glycerides\b|\bmonoglycerides\b", "mono- & diglycerides"),
    (r"\b(glycerin[e]?|glycerol)\b", "glycerin"),
    (r"\b(tallow|suet|animal fat|animal shortening)\b", "animal fat"),
    (r"\bwine vinegar\b", "wine vinegar"),
]
# Things that make the above fine, removed from the text before checking.
DOUBTFUL_OK = (r"\b(fish|halal|vegetable|plant|plant-based|vegetarian|marine) (gelatin[e]?|collagen|glycerin[e]?|glycerol)\b"
               r"|\b(microbial|bacterial|vegetable|plant|fungal|non-animal|vegetarian) (rennet|enzymes?|coagulant)\b"
               r"|\blactase( enzyme)?\b|\b(mono-? ?(and|&) ?di-?glycerides|glycerides) \(?(of )?(vegetable|plant)[^,;)]*\)?")
# Softer: usually fine, but some people ask the maker. Shown as a note; does not fail the filter.
CHECK_WORDS = [
    (r"\b(natural )?(flavou?r(ing)?s?|arômes? naturels?)\b", "flavourings"),
    (r"\bvanilla extract\b", "vanilla extract (made with alcohol)"),
]
# Animal-derived (not meat itself) -> not vegetarian / vegan / pescatarian.
ANIMAL_DERIVED = (r"\b(gelatin[e]?|gélatine|collagen|collagène|rennet|présure|lard|tallow|suet|animal fat|animal shortening|"
                  r"bone (broth|phosphate|char)|"
                  r"carmine|cochineal|carminic acid|isinglass)\b")
VEG_RENNET_OK = r"\b(microbial|vegetable|plant|fungal|non-animal|vegetarian) (rennet|présure)\b"
FISH_DERIVED_OK = r"\b(fish|marine) (gelatin[e]?|collagen)\b|\bisinglass\b"
MEAT = r"\b(chicken|poulet|turkey|dinde|lamb|agneau|mutton|goat|duck|canard|venison|meat|viande|beef|pork|veal)\b"
FISH = r"\b(fish|poisson|salmon|saumon|tuna|thon|sardine|cod|morue|tilapia|trout|mackerel|anchov\w*|herring|pollock|haddock)\b"
SHELLFISH = r"\b(shrimp|prawn|crab|lobster|crayfish|clam|mussel|oyster|scallop|squid|octopus|crevette|homard)\b"
GLUTEN_WORDS = r"\b(wheat|blé|barley|orge|rye|seigle|spelt|épeautre|malt|triticale|kamut|semolina|durum|farro|bulgur|couscous|seitan)\b"
OATS = r"\b(oats?|oat flour|avoine)\b"
SUGARS = r"\b(sugar|sucre|syrup|sirop|dextrose|glucose|fructose|sucrose|maltose|honey|miel|molasses|agave|cane juice|maltodextrin)\b"
DAIRY_WORDS = r"\b(milk|lait|cream|crème|butter|beurre|cheese|fromage|whey|lactosérum|casein|caséine|yogurt|yaourt|lactose|ghee)\b"
PLANT_MILKS = r"\b(coconut|almond|oat|soy|soya|rice|cashew|cocoa|peanut|shea|nut) (milk|butter|cream)\b"

DOUBTFUL_E = {"e120": "carmine (E120)", "e441": "gelatin (E441)", "e542": "bone phosphate (E542)",
              "e904": "shellac (E904)", "e920": "L-cysteine (E920)", "e921": "L-cystine (E921)",
              "e422": "glycerin (E422)", "e471": "mono- & diglycerides (E471)", "e472a": "E472a", "e472b": "E472b",
              "e472c": "E472c", "e472e": "E472e", "e481": "E481", "e482": "E482", "e491": "E491"}
ANIMAL_E = {"e120", "e441", "e542"}
VINEGARS = r"\b(wine|sherry|malt|cider) vinegar\b"
GLYCERIN = r"\b(glycerin[e]?|glycerol)\b"
GF_WORD = r"gluten[- ]free"
HARAM_E = {"e1510"}

ALLERGEN = {  # Betty name -> Open Food Facts allergen tag(s)
    "gluten": ["en:gluten"], "milk": ["en:milk"], "eggs": ["en:eggs"], "nuts": ["en:nuts"],
    "peanuts": ["en:peanuts"], "soy": ["en:soybeans"], "sesame": ["en:sesame-seeds"],
    "fish": ["en:fish"], "shellfish": ["en:crustaceans", "en:molluscs"], "mustard": ["en:mustard"],
    "celery": ["en:celery"], "sulphites": ["en:sulphur-dioxide-and-sulphites"], "lupin": ["en:lupin"],
}
# Ingredient words per allergen: a second check, because Open Food Facts' allergen tags are
# often missing (volunteers fill them in). Any match fails that "free-from" filter.
ALLERGEN_WORDS = {
    "gluten": GLUTEN_WORDS, "milk": DAIRY_WORDS, "fish": FISH, "shellfish": SHELLFISH,
    "eggs": r"\b(eggs?|oeufs?|œufs?|albumen|egg whites?|egg yolks?|mayonnaise)\b",
    "nuts": (r"\b(nuts?|almonds?|hazelnuts?|walnuts?|cashews?|pecans?|pistachios?|macadamias?|praline|marzipan|"
             r"amandes?|noisettes?|noix|pistaches?|pralin[ée]?)\b"),
    "peanuts": r"\b(peanuts?|groundnuts?|arachides?|cacahu[eè]tes?)\b",
    "soy": r"\b(soy|soya|soybeans?|soja|edamame|tofu|tempeh|miso)\b",
    "sesame": r"\b(sesame|sésame|tahini|tahina)\b",
    "mustard": r"\b(mustard|moutarde)\b",
    "celery": r"\b(celery|céleri|celeriac)\b",
    "sulphites": r"\b(sul(ph|f)ites?|sul(ph|f)ur dioxide|(meta|bi)sul(ph|f)ites?)\b",
    "lupin": r"\blupin[e]?s?\b",
}
NOT_ALLERGEN = r"\bnoix de (coco|muscade)\b"      # French: coconut, nutmeg

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
    ingr_wo_vinegar = re.sub(VINEGARS, "vinegar", ingr, flags=re.I)
    pork = _has(PORK, text) or "en:pork" in cats or "en:pork" in allergens
    beef = _has(BEEF, text) or "en:beef" in cats or "en:beef" in allergens
    alcohol = _has(ALCOHOL, ingr_wo_vinegar) or bool(adds & HARAM_E) or "en:contains-alcohol" in labels
    ingr_ok = re.sub(DOUBTFUL_OK, " ", ingr, flags=re.I)
    doubtful_why = [label for rx, label in DOUBTFUL_WORDS if _has(rx, ingr_ok)]
    if "en:gelatin" in allergens and "gelatin" not in doubtful_why:
        doubtful_why.append("gelatin")
    plain_glycerin = _has(GLYCERIN, ingr_ok) or not _has(GLYCERIN, ingr)
    for code in sorted(adds & set(DOUBTFUL_E)):
        name_ = DOUBTFUL_E[code]
        if code == "e422" and not plain_glycerin:
            continue                              # "vegetable glycerin" spelled out
        if not any(name_.split(" (")[0] == d.split(" (")[0] for d in doubtful_why):
            doubtful_why.append(name_)
    doubtful = bool(doubtful_why)
    check_why = [label for rx, label in CHECK_WORDS if _has(rx, ingr)]
    ingr_veg = re.sub(VEG_RENNET_OK, " ", ingr, flags=re.I)
    # animal_derived: not ok for pescatarians (fish gelatin is); any_animal: not ok for vegetarians/vegans
    animal_derived = (_has(ANIMAL_DERIVED, re.sub(FISH_DERIVED_OK, " ", ingr_veg, flags=re.I))
                      or bool(adds & ANIMAL_E))
    any_animal = animal_derived or _has(ANIMAL_DERIVED, ingr_veg)
    meat = _has(MEAT, text) or any(c in cats for c in ("en:meats", "en:poultries", "en:chickens"))
    fish = _has(FISH, text) or "en:fish" in allergens or "en:fishes" in cats
    shellfish = _has(SHELLFISH, text) or bool({"en:crustaceans", "en:molluscs"} & allergens)

    vegan = (("en:vegan" in analysis or any("vegan" in l and "non-vegan" not in l for l in labels))
             and "en:non-vegan" not in analysis and not meat and not fish and not any_animal)
    vegetarian = vegan or (("en:vegetarian" in analysis
                            or any("vegetarian" in l and "non-" not in l for l in labels))
                           and "en:non-vegetarian" not in analysis and not meat and not fish
                           and not any_animal)
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

    ingr_allergen = re.sub(NOT_ALLERGEN, " ", ingr, flags=re.I)

    def free_of(key):
        """True only with an ingredient list, and no allergen tag, 'may contain' tag or ingredient word for it."""
        if not known:
            return False
        tags = set(ALLERGEN[key])
        if tags & allergens or tags & traces:
            return False
        words = re.sub(PLANT_MILKS, " ", ingr_allergen, flags=re.I) if key == "milk" else ingr_allergen
        return not _has(ALLERGEN_WORDS[key], words)

    gf_cert = bool(labels & GLUTEN_FREE_LABELS)
    gluten_free = gf_cert or (free_of("gluten") and not _has(GLUTEN_WORDS, ingr)
                              and (not _has(OATS, ingr) or _has(GF_WORD, ingr)))
    ingr_no_plant_milk = re.sub(PLANT_MILKS, "", ingr, flags=re.I)
    dairy_free = vegan or (free_of("milk") and not _has(DAIRY_WORDS, ingr_no_plant_milk))
    lactose_free = bool(labels & LACTOSE_FREE_LABELS) or dairy_free
    no_added_sugar = "en:no-added-sugar" in labels or (known and not _has(SUGARS, ingr))
    palm_free = "en:palm-oil-free" in analysis or "en:no-palm-oil" in labels
    pescatarian = vegetarian or (known and not meat and not pork and not beef and not animal_derived)

    return dict(
        known_ingredients=known, pork=pork, beef=beef, alcohol=alcohol, doubtful=doubtful, doubtful_why=doubtful_why,
        check_why=check_why, meat=meat,
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
        why = [x for x, on in (("pork", flags["pork"]), ("alcohol", flags["alcohol"])) if on]
        w.append("not halal" + (f" ({', '.join(why)})" if why else ""))
    elif flags["halal"] == "doubtful":
        w.append("halal doubtful: " + ", ".join(flags["doubtful_why"]))
    elif flags["halal"] == "not-certified-meat":
        w.append("meat not halal-certified")
    if flags["halal"] in ("ok-by-ingredients", "doubtful") and flags["check_why"]:
        w.append("halal: check " + " & ".join(flags["check_why"]))
    if not flags["known_ingredients"]:
        w.append("no ingredient list: additives unchecked")
    return w
