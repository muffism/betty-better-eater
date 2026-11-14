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


# ---------------- new diets & badges
from betty.diet import badges, DIETS  # noqa: E402


def Q(ingr, labels=(), allergens=(), traces=(), analysis=(), name="x"):
    return dict(product_name=name, ingredients_text=ingr, labels_tags=list(labels), allergens_tags=list(allergens),
                traces_tags=list(traces), ingredients_analysis_tags=list(analysis), categories_tags=[], additives_tags=[])


def test_badges_show_only_what_applies():
    f = classify(Q("organic chickpeas, water, sea salt", labels=["en:orthodox-union-kosher"],
                   analysis=["en:vegan"]))
    assert badges(f) == ["Halal (ingredients)", "Kosher", "Vegan", "Gluten-free", "Dairy-free", "Nut-free",
                         "Egg-free", "Soy-free", "No added sugar"]
    milk_choc = classify(Q("sugar, milk, cocoa butter, wheat flour, hazelnuts", allergens=["en:milk", "en:gluten", "en:nuts"]))
    b = badges(milk_choc)
    assert "Vegan" not in b and "Gluten-free" not in b and "Dairy-free" not in b and "Nut-free" not in b
    assert "No added sugar" not in b


def test_may_contain_counts_as_containing():
    f = classify(Q("oats", traces=["en:nuts"], labels=["en:no-gluten"]))
    assert not passes(f, {"nut-free"}) and passes(f, {"gluten-free"})


def test_missing_ingredients_fail_free_from_filters():
    f = classify(Q(""))
    assert not passes(f, {"peanut-free"}) and not passes(f, {"gluten-free"}) and badges(f) == []


def test_plain_oats_not_gluten_free_without_label():
    assert not passes(classify(Q("rolled oats")), {"gluten-free"})
    assert passes(classify(Q("gluten-free rolled oats")), {"gluten-free"})


def test_lactose_free_milk_and_plant_milk():
    lf = classify(Q("milk, lactase enzyme", labels=["en:no-lactose"], allergens=["en:milk"]))
    assert passes(lf, {"lactose-free"}) and not passes(lf, {"dairy-free"})
    coco = classify(Q("coconut milk, water, guar gum"))
    assert passes(coco, {"dairy-free"})


def test_kosher_needs_label_and_every_diet_is_listed():
    assert not passes(classify(Q("water, salt")), {"kosher"})
    assert passes(classify(Q("water, salt", labels=["en:kosher-parve"])), {"kosher"})
    assert {"halal", "kosher", "vegan", "gluten-free", "lactose-free", "nut-free", "egg-free"} <= set(DIETS)


# ---------------- gelatin & other hidden animal / alcohol sources
from betty.diet import warnings  # noqa: E402


def test_gummies_with_gelatin_are_doubtful_and_not_vegetarian_or_pescatarian():
    f = classify(Q("glucose syrup, sugar, gelatin, citric acid, carmine", analysis=["en:non-vegan"]))
    assert f["halal"] == "doubtful" and f["doubtful_why"] == ["gelatin", "carmine"]
    assert not passes(f, {"halal"}) and not passes(f, {"pescatarian"}) and not passes(f, {"vegetarian"})
    assert "halal doubtful: gelatin, carmine" in warnings(f)


def test_pork_gelatin_is_haram_and_fish_or_halal_gelatin_is_fine():
    assert classify(Q("sugar, pork gelatin"))["halal"] == "not-halal"
    assert "not halal (pork)" in warnings(classify(Q("sugar, pork gelatin")))
    fish = classify(Q("sugar, fish gelatin, citric acid"))
    assert fish["halal"] == "ok-by-ingredients" and passes(fish, {"pescatarian"}) and not passes(fish, {"vegetarian"})
    assert classify(Q("sugar, halal gelatin"))["halal"] == "ok-by-ingredients"


def test_certified_halal_label_wins_over_gelatin():
    assert classify(Q("sugar, gelatin", labels=["en:halal"]))["halal"] == "certified"


def test_cheese_enzymes_microbial_ok_animal_rennet_doubtful():
    ok = classify(Q("pasteurized milk, bacterial culture, salt, microbial enzyme", analysis=["en:vegetarian"]))
    assert ok["halal"] == "ok-by-ingredients" and passes(ok, {"vegetarian"})
    bad = classify(Q("milk, salt, rennet", analysis=["en:vegetarian"]))
    assert bad["halal"] == "doubtful" and not passes(bad, {"vegetarian"})
    assert classify(Q("milk, salt, enzymes"))["doubtful_why"] == ["enzymes (source not stated)"]


def test_e_numbers_are_named():
    f = classify(dict(Q("sugar, emulsifier (e471)"), additives_tags=["en:e471", "en:e441"]))
    assert set(f["doubtful_why"]) == {"mono- & diglycerides (E471)", "gelatin (E441)"}


def test_vegetable_glycerin_ok_plain_glycerin_doubtful():
    assert classify(dict(Q("dates, vegetable glycerin"), additives_tags=["en:e422"]))["halal"] == "ok-by-ingredients"
    assert classify(Q("dates, glycerin"))["doubtful_why"] == ["glycerin"]


def test_flavourings_and_vanilla_are_a_note_not_a_fail():
    f = classify(Q("oats, sugar, natural flavour, vanilla extract", analysis=["en:vegan"]))
    assert f["halal"] == "ok-by-ingredients" and passes(f, {"halal"})
    assert "halal: check flavourings & vanilla extract (made with alcohol)" in warnings(f)
    assert not any("check" in w for w in warnings(classify(Q("oats, salt"))))


def test_alternatives_skip_brand_tags_typed_as_categories():
    from betty.cli import similar_categories
    cats = similar_categories({"categories_hierarchy": ["en:spreads", "en:sweet-spreads", "fr:Nutella",
                                                       "en:hazelnut-spreads"]})
    assert cats == ["en:hazelnut-spreads", "en:sweet-spreads"]


def test_allergens_caught_from_ingredients_when_tags_are_missing():
    # real case: Open Food Facts had no allergen tags in its export, but almonds were in the ingredients
    f = classify(Q("whole grain rolled oats, vegetable oil, almonds, sugars (honey blend, sugar), salt"))
    assert not passes(f, {"nut-free"}) and passes(f, {"peanut-free", "egg-free", "soy-free"})
    assert not passes(classify(Q("sugar, peanuts, salt")), {"peanut-free"})
    assert not passes(classify(Q("flour, sesame seeds, soy lecithin")), {"sesame-free"})
    assert not passes(classify(Q("flour, sesame seeds, soy lecithin")), {"soy-free"})
    assert not passes(classify(Q("pasta, egg yolks")), {"egg-free"})
    assert not passes(classify(Q("vinegar, mustard seed")), {"mustard-free"})
    # not allergens: coconut, nutmeg, eggplant, nutritional yeast, coconut milk for dairy
    f = classify(Q("coconut, nutmeg, noix de coco, eggplant, nutritional yeast, coconut milk"))
    assert passes(f, {"nut-free", "egg-free", "dairy-free"})
