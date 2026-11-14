"""Yuka-style 0-100 estimate.

Yuka publishes its method (help.yuka.io, "How are food products rated?"):
  * 60 %  nutritional quality, from the Nutri-Score (original algorithm),
          converted with Yuka's own correspondence table (reproduced below);
  * 30 %  additives: each additive has a risk level; one high-risk additive
          caps the whole product at 49/100;
  * 10 %  organic: a bonus for an official organic label;
  * Nutri-Score D/E products can never exceed 49.

This module is an independent re-implementation of that published method.
It is NOT Yuka's code and the results are estimates. The exact weight Yuka
gives to low/moderate-risk additives is not public; we approximate it.
"""
from dataclasses import dataclass, field

# Yuka's published table: Nutri-Score points -> nutrition rating (0-100)
SOLID = {-2: 100, -1: 90, 0: 80, 1: 75, 2: 70, 3: 65, 4: 60, 5: 55, 6: 50, 7: 45, 8: 40,
         9: 35, 10: 30, 11: 15, 12: 13, 13: 11, 14: 9, 15: 7, 16: 5, 17: 3, 18: 1}
LIQUID = {-3: 77, -2: 74, -1: 71, 0: 68, 1: 65, 2: 57, 3: 49, 4: 41, 5: 33, 6: 15,
          7: 11, 8: 7, 9: 3}

# Approximate cost of one additive in the 0-100 additive sub-score
ADDITIVE_COST = {"risk-free": 0, "limited": 10, "moderate": 25, "high": 100, "unknown": 10}


# Betty's five bands (Yuka itself shows four: 75+, 50-74, 25-49, 0-24)
BANDS = [("Excellent", 90), ("Very good", 75), ("Good", 50), ("Bad", 25), ("Very bad", 0)]


def band(score: int) -> str:
    for name, floor in BANDS:
        if score >= floor:
            return name
    return "Very bad"


def band_floor(name: str) -> int:
    """'excellent' -> 90, 'very-good' -> 75 ... (case/space/dash-insensitive)."""
    key = name.lower().replace("-", " ").replace("_", " ").strip()
    for n, floor in BANDS:
        if n.lower() == key:
            return floor
    raise ValueError(f"Unknown band '{name}'. Choose from: " + ", ".join(n for n, _ in BANDS))


def nutrition_rating(pts: int, beverage=False) -> int:
    if beverage:
        return 80 if pts <= -4 else LIQUID.get(pts, 0)
    if pts <= -2:
        return 100
    return 0 if pts >= 19 else SOLID[pts]


@dataclass
class Estimate:
    score: int
    nutrition_rating: int
    additive_rating: int
    organic: bool
    nutriscore_points: int
    capped_reason: str | None = None
    flagged_additives: list = field(default_factory=list)

    @property
    def label(self):
        return band(self.score)


def estimate(nutriscore_points: int, organic: bool, additive_risks: dict | None = None,
             beverage=False) -> Estimate:
    """additive_risks: {"e330": "risk-free", "e250": "high", ...}"""
    additive_risks = additive_risks or {}
    n = nutrition_rating(nutriscore_points, beverage)
    a = 100 - sum(ADDITIVE_COST.get(r, 10) for r in additive_risks.values())
    a = max(0, a)
    s = 0.6 * n + 0.3 * a + 0.1 * (100 if organic else 0)
    cap = None
    if any(r == "high" for r in additive_risks.values()):
        s, cap = min(s, 49), "high-risk additive"
    if not beverage and nutriscore_points >= 11:
        s, cap = min(s, 49), cap or "Nutri-Score D/E"
    flagged = sorted(k for k, r in additive_risks.items() if r != "risk-free")
    return Estimate(round(s), n, a, organic, nutriscore_points, cap, flagged)
