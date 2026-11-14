"""Additive risk levels.

Yuka does not publish its additive list as a dataset, so Betty combines:
  1. Open Food Facts' additives taxonomy (ODbL), which carries EFSA
     over-exposure evaluations (high / moderate / no) and the ANSES
     "additives of interest" flag;
  2. a small curated override list (data/additive_overrides.json), based on
     public Yuka additive pages and EFSA opinions, editable by anyone.
Anything unknown is treated as "limited" (a small penalty) and flagged so a
human can check it.
"""
import json, os, time
from functools import lru_cache
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "betty")
TAXONOMY_URL = "https://static.openfoodfacts.org/data/taxonomies/additives.json"
UA = {"User-Agent": "BettyBetterEater/0.2 (+https://github.com/muffism/betty-better-eater)"}


def _norm(code: str) -> str:
    return code.lower().replace("en:", "").replace(" ", "").replace("-", "")


@lru_cache(maxsize=1)
def overrides() -> dict:
    with open(os.path.join(HERE, "data", "additive_overrides.json"), encoding="utf-8") as f:
        raw = json.load(f)
    out = {}
    for level, codes in raw["levels"].items():
        for c in codes:
            out[_norm(c)] = level
    return out


@lru_cache(maxsize=1)
def taxonomy() -> dict:
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "additives.json")
    if not os.path.exists(path) or time.time() - os.path.getmtime(path) > 30 * 86400:
        try:
            r = requests.get(TAXONOMY_URL, headers=UA, timeout=60)
            r.raise_for_status()
            with open(path, "w", encoding="utf-8") as f:
                f.write(r.text)
        except Exception:
            if not os.path.exists(path):
                return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def risk(code: str) -> str:
    c = _norm(code)
    ov = overrides()
    if c in ov:
        return ov[c]
    # parent code (e.g. e322i -> e322)
    base = c.rstrip("abcdefghijklmnopqrstuvwxyz") if c[:1] == "e" else c
    if base in ov:
        return ov[base]
    t = taxonomy().get("en:" + c) or taxonomy().get("en:" + base) or {}
    lvl = (t.get("efsa_evaluation_overexposure_risk") or {}).get("en", "")
    if lvl.endswith("high"):
        return "high"
    if lvl.endswith("moderate") or (t.get("anses_additives_of_interest") or {}).get("en") == "yes":
        return "moderate"
    if lvl.endswith("no"):
        return "risk-free"
    return "unknown"


def risks(codes) -> dict:
    return {_norm(c): risk(c) for c in codes or []}
