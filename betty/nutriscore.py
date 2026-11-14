"""Nutri-Score, original (2017) algorithm, the version Yuka says it still uses.

Reference: Santé publique France, Nutri-Score specifications (2017).
Per 100 g (or 100 mL for beverages).
"""
from dataclasses import dataclass


def _steps(value, thresholds):
    return sum(1 for t in thresholds if value > t)


@dataclass
class Nutrition:
    kcal: float = 0.0
    sugars: float = 0.0
    sat_fat: float = 0.0
    sodium_mg: float = 0.0
    fibre: float = 0.0
    protein: float = 0.0
    fvn_pct: float = 0.0          # fruit, vegetables, legumes, nuts (+ olive/walnut/rapeseed oil)
    fat: float | None = None      # needed for the fats/oils rule


def points(n: Nutrition, *, beverage=False, cheese=False, added_fat=False) -> int:
    """Return Nutri-Score points (lower is better)."""
    kj = n.kcal * 4.184
    if beverage:
        neg = _steps(kj, [0, 30, 60, 90, 120, 150, 180, 210, 240, 270])
        neg += _steps(n.sugars, [0, 1.5, 3, 4.5, 6, 7.5, 9, 10.5, 12, 13.5])
    else:
        neg = _steps(kj, [335 * i for i in range(1, 11)])
        neg += _steps(n.sugars, [4.5, 9, 13.5, 18, 22.5, 27, 31, 36, 40, 45])
    if added_fat and n.fat:
        neg += _steps(n.sat_fat / n.fat * 100, [10, 16, 22, 28, 34, 40, 46, 52, 58, 64])
    else:
        neg += _steps(n.sat_fat, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    neg += _steps(n.sodium_mg, [90 * i for i in range(1, 11)])

    if beverage:
        fv = 10 if n.fvn_pct > 80 else 4 if n.fvn_pct > 60 else 2 if n.fvn_pct > 40 else 0
    else:
        fv = 5 if n.fvn_pct > 80 else 2 if n.fvn_pct > 60 else 1 if n.fvn_pct > 40 else 0
    fi = _steps(n.fibre, [0.9, 1.9, 2.8, 3.7, 4.7])
    pr = _steps(n.protein, [1.6, 3.2, 4.8, 6.4, 8.0])
    if neg >= 11 and fv < (10 if beverage else 5) and not cheese:
        return neg - fv - fi
    return neg - fv - fi - pr


def grade(pts: int, beverage=False, water=False) -> str:
    if water:
        return "A"
    if beverage:
        return "B" if pts <= 1 else "C" if pts <= 5 else "D" if pts <= 9 else "E"
    return "A" if pts <= -1 else "B" if pts <= 2 else "C" if pts <= 10 else "D" if pts <= 18 else "E"
