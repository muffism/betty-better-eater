"""Friendly shortcuts -> Open Food Facts category tags.
Any real OFF tag (e.g. 'en:canned-chickpeas') also works directly."""

SHORTCUTS = {
    # protein
    "chicken": "en:chickens", "poultry": "en:poultries", "fish": "en:fishes",
    "canned-fish": "en:canned-fishes", "salmon": "en:salmons", "tuna": "en:tunas",
    "sardines": "en:sardines", "eggs": "en:eggs", "tofu": "xx:tofu",
    "beans": "en:common-beans", "chickpeas": "en:chickpeas", "lentils": "en:lentils",
    "legumes": "en:legumes", "hummus": "en:hummus",
    # grains
    "oats": "en:rolled-oats", "cereal": "en:breakfast-cereals", "granola": "en:mueslis",
    "rice": "en:rices", "quinoa": "en:quinoa", "pasta": "en:pastas", "noodles": "en:noodles",
    "bread": "en:breads", "flour": "en:flours", "crackers": "en:biscuits-and-crackers", "tortillas": "en:tortillas",
    # fruit & veg
    "frozen-vegetables": "en:frozen-vegetables", "frozen-fruit": "en:frozen-fruits",
    "berries": "en:berries", "vegetables": "en:vegetables", "fruits": "en:fruits",
    "canned-tomatoes": "en:canned-tomatoes", "tomato-sauce": "en:tomato-sauces",
    "applesauce": "en:compotes", "dried-fruit": "en:dried-fruits",
    "guacamole": "en:guacamoles", "soup": "en:soups",
    # dairy & alternatives
    "yogurt": "en:yogurts", "milk": "en:milks", "cheese": "en:cheeses",
    "plant-milk": "en:plant-based-milk-alternatives", "kefir": "en:kefir",
    # snacks & pantry
    "nuts": "en:nuts", "seeds": "en:seeds", "chia": "en:chia", "nut-butter": "en:nut-butters",
    "peanut-butter": "en:peanut-butters", "snacks": "en:snacks", "bars": "en:cereal-bars",
    "chips": "en:chips-and-fries", "chocolate": "en:chocolates", "cookies": "en:biscuits",
    "spices": "en:spices", "olive-oil": "en:olive-oils", "honey": "en:honeys",
    "baby-food": "en:baby-foods", "juice": "en:fruit-juices", "tea": "en:teas", "coffee": "en:coffees",
}


def resolve(name: str) -> str:
    n = name.strip().lower().replace(" ", "-")
    if ":" in n:
        return n
    if n in SHORTCUTS:
        return SHORTCUTS[n]
    if n.endswith("s") and n[:-1] in SHORTCUTS:
        return SHORTCUTS[n[:-1]]
    return "en:" + n
