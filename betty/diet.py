"""Diet filters: no-beef, no-pork, halal-friendly, vegetarian, vegan.

IMPORTANT: "halal-friendly (by ingredients)" only means nothing in the
ingredient list is known to be haram or doubtful. It is NOT a religious
ruling and NOT a certification. Only a label from a recognised halal
certifier (shown as `certified`) confirms halal status.
"""
import re

PORK = r"\b(pork|porc|bacon|ham|jambon|lard|saindoux|prosciutto|pancetta|chorizo|salami|pepperoni|gelatin[e]? \(pork\)|pig|swine)\b"
BEEF = r"\b(beef|boeuf|bœuf|veal|veau|brisket|bison)\b"
ALCOHOL = r"\b(wine|vin|beer|bière|rum|rhum|brandy|cognac|whisk(e)?y|vodka|liqueur|alcohol|alcool|ethanol|ethyl alcohol|mirin|sake)\b"
DOUBTFUL = r"\b(gelatin[e]?|gélatine|rennet|présure|carmine|cochineal|l-cysteine|shellac|natural flavou?r|mono- and diglycerides)\b"
MEAT = r"\b(chicken|poulet|turkey|dinde|lamb|agneau|mutton|goat|duck|canard|venison|meat|viande)\b"
SEAFOOD = r"\b(fish|salmon|saumon|tuna|thon|sardine|cod|morue|tilapia|trout|mackerel|anchov|herring|shrimp|prawn|crab|lobster)\b"

DOUBTFUL_E = {"e120", "e441", "e542", "e904", "e920", "e921", "e471", "e472a", "e472b", "e472c",
              "e472e", "e481", "e482", "e491"}
HARAM_E = {"e1510"}  # ethanol


def _has(rx, text):
    return re.search(rx, text, flags=re.I) is not None


def classify(product: dict) -> dict:
    """Return flags for an Open Food Facts product dict."""
    ingr = " ".join(filter(None, [product.get("ingredients_text_en"), product.get("ingredients_text")]))
    name = product.get("product_name") or ""
    cats = " ".join(product.get("categories_tags") or [])
    labels = product.get("labels_tags") or []
    analysis = product.get("ingredients_analysis_tags") or []
    adds = {a.replace("en:", "") for a in product.get("additives_tags") or []}
    text = f"{name} {ingr} {cats}"

    pork = _has(PORK, text) or "en:pork" in cats or "en:pork-meat" in cats
    beef = _has(BEEF, text) or "en:beef" in cats
    # "wine vinegar" is considered halal by most scholars (the alcohol has turned to vinegar),
    # so it is flagged as doubtful for the user to decide, not as alcohol.
    wine_vinegar = _has(r"\b(wine|cider|malt|sherry) vinegar\b", ingr)
    ingr_wo_vinegar = re.sub(r"\b(wine|sherry|malt) vinegar\b", "vinegar", ingr, flags=re.I)
    alcohol = _has(ALCOHOL, ingr_wo_vinegar) or bool(adds & HARAM_E)
    doubtful = (_has(DOUBTFUL, ingr) or bool(adds & DOUBTFUL_E)
                or _has(r"\bwine vinegar\b", ingr))
    meat = _has(MEAT, text) or "en:meats" in cats or "en:poultries" in cats
    certified = any("halal" in l for l in labels)
    vegan = "en:vegan" in analysis or "en:vegan" in labels
    vegetarian = vegan or "en:vegetarian" in analysis or "en:vegetarian" in labels

    if certified and not pork and not alcohol:
        halal = "certified"
    elif pork or alcohol:
        halal = "not-halal"
    elif meat:
        halal = "not-certified-meat"     # meat must be certified to be halal
    elif doubtful:
        halal = "doubtful"
    elif not ingr:
        halal = "unknown"
    else:
        halal = "ok-by-ingredients"
    return dict(pork=pork, beef=beef, alcohol=alcohol, doubtful=doubtful, meat=meat, wine_vinegar=wine_vinegar,
                seafood=_has(SEAFOOD, text), vegan=vegan, vegetarian=vegetarian, halal=halal)


def passes(flags: dict, diet: set) -> bool:
    """diet: any of {'no-pork','no-beef','halal','halal-strict','vegetarian','vegan'}.
    'halal'        -> certified, or ok-by-ingredients for non-meat products
    'halal-strict' -> certified only
    """
    if "no-pork" in diet and flags["pork"]:
        return False
    if "no-beef" in diet and flags["beef"]:
        return False
    if "halal-strict" in diet and flags["halal"] != "certified":
        return False
    if "halal" in diet and flags["halal"] not in ("certified", "ok-by-ingredients"):
        return False
    if "vegetarian" in diet and not flags["vegetarian"]:
        return False
    if "vegan" in diet and not flags["vegan"]:
        return False
    return True
