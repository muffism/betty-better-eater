"""Fast offline mode: a tiny fake Open Food Facts export instead of the real 1.5 GB one."""
import gzip, io

import pytest

from betty import local, off, cli

HEADER = ["code", "product_name", "brands", "brands_tags", "quantity", "stores", "countries_tags", "labels_tags",
          "categories_tags", "ingredients_text", "allergens", "traces_tags", "additives_tags",
          "ingredients_analysis_tags", "unique_scans_n", "image_url", "image_small_url", "energy-kcal_100g",
          "fat_100g", "saturated-fat_100g", "sugars_100g", "sodium_100g", "fiber_100g", "proteins_100g",
          "fruits-vegetables-legumes_100g"]

ROWS = [
    dict(code="111", product_name="Organic Rolled Oats", brands="Kirkland Signature", brands_tags="kirkland-signature",
         stores="Costco, Walmart", countries_tags="en:canada,en:united-states", labels_tags="en:organic",
         categories_tags="en:cereals-and-potatoes,en:breakfast-cereals,en:rolled-oats", ingredients_text="organic oats",
         unique_scans_n="50", **{"energy-kcal_100g": "380", "sugars_100g": "1", "saturated-fat_100g": "1.2",
                                 "sodium_100g": "0", "fiber_100g": "10", "proteins_100g": "13"}),
    dict(code="222", product_name="Honey Oat Clusters", brands="Sweet Co", brands_tags="sweet-co", stores="Walmart",
         countries_tags="en:canada", categories_tags="en:breakfast-cereals,en:rolled-oats",
         ingredients_text="oats, sugar, gelatin, honey", allergens="en:gluten", unique_scans_n="90",
         **{"energy-kcal_100g": "450", "sugars_100g": "30", "saturated-fat_100g": "4", "sodium_100g": "0.3",
            "fiber_100g": "4", "proteins_100g": "7"}),
    dict(code="333", product_name="French Oats", countries_tags="en:france", categories_tags="en:rolled-oats",
         ingredients_text="avoine", **{"energy-kcal_100g": "380"}),
    dict(code="444", product_name="Canadian Bacon", countries_tags="en:canadas-fake",   # must not match en:canada
         categories_tags="en:meats", ingredients_text="pork"),
]


def _dump():
    buf = io.StringIO()
    buf.write("\t".join(HEADER) + "\n")
    for r in ROWS:
        buf.write("\t".join(r.get(h, "") for h in HEADER) + "\n")
    return gzip.compress(buf.getvalue().encode())


class FakeResp:
    def __init__(self, body):
        self.raw, self.headers = io.BytesIO(body), {"content-length": str(len(body))}

    def raise_for_status(self):
        pass


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(local, "HOME", str(tmp_path))
    monkeypatch.setattr(local, "SETTINGS", str(tmp_path / "settings.json"))
    monkeypatch.setattr(local, "DISABLED", False)
    monkeypatch.setattr(local.requests, "get", lambda *a, **k: FakeResp(_dump()))
    return tmp_path


def test_download_keeps_only_that_country(home):
    assert local.download("Canada", out=io.StringIO()) == 2
    a = local.active()
    assert a["country"] == "canada" and a["products"] == 2
    assert local.product("333") == {} and local.product("444") == {}
    p = local.product("111")
    assert p["stores_tags"] == ["costco", "walmart"] and p["labels_tags"] == ["en:organic"]
    assert p["nutriments"]["fiber_100g"] == 10


def test_offline_search_and_scores(home):
    local.download("canada", out=io.StringIO())
    assert [p["code"] for p in off.search(category="rolled-oats", country="canada")] == ["222", "111"]  # by scans
    assert [p["code"] for p in off.search(category="en:rolled-oats", store="costco")] == ["111"]
    assert [p["code"] for p in off.search(terms="oat honey", country="canada")] == ["222"]
    assert [p["code"] for p in off.search(category="rolled-oats", brand="Kirkland Signature")] == ["111"]
    assert [p["code"] for p in off.search(category="rolled-oats", organic=True)] == ["111"]
    assert off.search(category="rolled-oats", page=2) == []
    r = off.evaluate(local.product("111"))
    assert r["score"] == 100 and r["organic"] and "Halal" in " ".join(r["fits"])
    assert "halal doubtful: gelatin" in off.evaluate(local.product("222"))["warnings"]


def test_store_list_fills_in_blank_stores_in_the_export(home, monkeypatch):
    local.download("canada", out=io.StringIO())
    calls = []

    def fake_get(url, params, kind):
        calls.append(params)
        return {"count": 1, "products": [{"code": "222"}]}        # live site: 222 is at Costco too
    monkeypatch.setattr(off, "_get", fake_get)
    got = off.search(category="rolled-oats", store="Costco")
    assert sorted(p["code"] for p in got) == ["111", "222"]
    assert next(p for p in got if p["code"] == "222")["stores"] == "Walmart, Costco"
    assert calls[0]["stores_tags"] == "costco" and calls[0]["countries_tags_en"] == "canada"
    off.search(category="rolled-oats", store="costco")
    assert len(calls) == 1                                          # kept, not fetched again

    monkeypatch.setattr(off, "_get", lambda *a: {})                 # no internet, nothing saved: export only
    assert [p["code"] for p in off.search(category="rolled-oats", store="walmart")] == ["222", "111"]


def test_other_countries_and_online_flag_go_online(home, monkeypatch):
    local.download("canada", out=io.StringIO())
    calls = []
    monkeypatch.setattr(off, "_get", lambda url, params, kind: calls.append(params) or {"products": []})
    off.search(category="rolled-oats", country="france")
    assert calls and calls[-1]["countries_tags_en"] == "france"
    monkeypatch.setattr(local, "DISABLED", True)
    off.search(category="rolled-oats", country="canada")
    assert len(calls) == 2


def test_remove_goes_back_online(home):
    local.download("canada", out=io.StringIO())
    local.remove()
    assert local.active() is None and not local.covers("canada")
    assert local.settings()["mode"] == "online"


def test_failed_download_leaves_nothing_behind(home, monkeypatch):
    monkeypatch.setattr(local.requests, "get", lambda *a, **k: FakeResp(_dump()[:60]))   # cut off mid-way
    with pytest.raises(Exception):
        local.download("canada", out=io.StringIO())
    assert local.active() is None
    assert not list(home.glob("*.db*"))


def test_first_run_asks_once_and_never_in_scripts(home, monkeypatch, capsys):
    class A:
        json, country = False, None
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False, raising=False)
    cli.first_run(A())
    assert "mode" not in local.settings()          # piped / scripted: no question asked
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(local, "dump_size", lambda: 1_536_000_000)
    answers = iter(["n"])
    monkeypatch.setattr("builtins.input", lambda q: next(answers))
    cli.first_run(A())
    out = capsys.readouterr().out
    assert local.settings()["mode"] == "online" and "staying online" in out
    cli.first_run(A())                              # asked once only (iterator would raise if asked again)


def test_first_run_yes_downloads(home, monkeypatch):
    class A:
        json, country = False, None
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(local, "dump_size", lambda: 0)
    answers = iter(["y", "Canada"])
    monkeypatch.setattr("builtins.input", lambda q: next(answers))
    a = A()
    cli.first_run(a)
    assert a.country == "canada" and local.covers("canada")
