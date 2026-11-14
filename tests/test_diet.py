from betty.diet import classify, passes


def P(ingr, name="x", labels=(), cats=(), adds=(), analysis=()):
    return dict(product_name=name, ingredients_text=ingr, labels_tags=list(labels),
                categories_tags=list(cats), additives_tags=list(adds), ingredients_analysis_tags=list(analysis))


def test_pork_is_excluded():
    f = classify(P("water, pork, salt"))
    assert f["pork"] and f["halal"] == "not-halal" and not passes(f, {"no-pork"})


def test_plant_food_is_halal_by_ingredients():
    f = classify(P("organic chickpeas, water, sea salt", analysis=["en:vegan"]))
    assert f["halal"] == "ok-by-ingredients" and passes(f, {"halal", "no-pork", "no-beef"})


def test_uncertified_chicken_is_not_halal_but_certified_is():
    assert classify(P("chicken", name="chicken breast"))["halal"] == "not-certified-meat"
    assert classify(P("chicken", name="chicken breast", labels=["en:halal"]))["halal"] == "certified"


def test_alcohol_and_gelatin():
    assert classify(P("sugar, wine vinegar, rum"))["alcohol"]
    assert classify(P("sugar, gelatin"))["halal"] == "doubtful"


def test_halal_strict_needs_certificate():
    f = classify(P("organic oats", analysis=["en:vegan"]))
    assert passes(f, {"halal"}) and not passes(f, {"halal-strict"})


def test_wine_vinegar_is_doubtful_not_alcohol():
    # most scholars consider wine vinegar halal; Betty flags it as doubtful so the user decides
    f = classify(P("water, red wine vinegar, salt"))
    assert not f["alcohol"] and f["halal"] == "doubtful"
    assert classify(P("avocado, white vinegar, salt"))["halal"] == "ok-by-ingredients"


def test_alternatives_use_specific_category_not_groceries():
    from betty.cli import similar_categories
    guac = {"categories_hierarchy": ["en:plant-based-foods-and-beverages", "en:plant-based-foods", "en:spreads",
                                     "en:condiments", "en:plant-based-spreads", "en:sauces", "en:dips",
                                     "en:guacamoles", "en:groceries"]}
    cats = similar_categories(guac)
    assert cats[0] == "en:guacamoles" and cats[1] == "en:dips" and "en:groceries" not in cats
