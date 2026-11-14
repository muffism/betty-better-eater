"""Checks against real Yuka scores that people have published online."""
from betty.nutriscore import Nutrition, points, grade
from betty.score import estimate, band, band_floor, nutrition_rating


def yuka(n, organic, additives=None, beverage=False):
    return estimate(points(n, beverage=beverage), organic, additives or {}, beverage=beverage).score


def test_yuka_table_matches_published_values():
    assert [nutrition_rating(p) for p in (-5, -2, -1, 0, 1, 2, 3, 10, 11, 18, 19)] == \
           [100, 100, 90, 80, 75, 70, 65, 30, 15, 1, 0]
    assert [nutrition_rating(p, beverage=True) for p in (-5, -1, 0, 3, 9, 10)] == [80, 71, 68, 49, 3, 0]


def test_organic_lentil_soup_scores_100():          # public scan: 100
    assert yuka(Nutrition(60, 1.2, 0.12, 48, 3.6, 3.2, 70), True) == 100


def test_organic_rolled_oats_score_100():           # public scan: 100
    assert yuka(Nutrition(375, 1.0, 1.3, 5, 10, 13), True) == 100


def test_non_organic_perfect_product_tops_out_at_90():   # hummus / peaches / tenders: 90
    assert estimate(-6, False).score == 90


def test_organic_milk_85():                          # KS Organic A2 milk: 85
    assert estimate(1, True).score == 85


def test_organic_coconut_water_81():                 # KS Organic coconut water: 81
    assert estimate(0, True, beverage=True).score == 81


def test_high_risk_additive_caps_at_49():
    assert estimate(-6, True, {"e250": "high"}).score == 49


def test_nutriscore_d_caps_at_49():
    assert estimate(12, True).score <= 49


def test_risk_free_additive_costs_nothing():
    assert estimate(-6, True, {"e330": "risk-free"}).score == 100


def test_bands_and_custom_threshold():
    assert [band(s) for s in (100, 90, 89, 75, 74, 50, 49, 25, 24, 0)] == \
        ["Excellent", "Excellent", "Very good", "Very good", "Good", "Good", "Bad", "Bad", "Very bad", "Very bad"]
    assert band_floor("very-good") == 75 and band_floor("Excellent") == 90


def test_grade_letters():
    assert grade(-1) == "A" and grade(0) == "B" and grade(3) == "C" and grade(11) == "D" and grade(19) == "E"
