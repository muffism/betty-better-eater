"""Guided mode: run `betty` with no arguments and answer a few questions."""
from .categories import SHORTCUTS


def _ask(q, default=""):
    try:
        a = input(f"{q}{f' [{default}]' if default else ''}: ").strip()
    except EOFError:
        a = ""
    return a or default


def _choose(q, options, default="1"):
    print(f"\n{q}")
    for i, (label, _) in enumerate(options, 1):
        print(f"  {i}. {label}")
    while True:
        a = _ask("Pick a number", default)
        if a.isdigit() and 1 <= int(a) <= len(options):
            return options[int(a) - 1][1]
        print("  Please type one of the numbers above.")


def run():
    print("\nHi, I'm Betty Better Eater. Let's find you healthier groceries.\n"
          "(Scores are estimates from Yuka's published method, using Open Food Facts data.)")
    action = _choose("What would you like to do?", [
        ("Check a product (barcode or name)", "score"),
        ("Find a better alternative to a product", "better"),
        ("Browse a category (e.g. oats, chicken, frozen-vegetables)", "browse"),
        ("Search by name", "find"),
        ("How does the score work?", "explain")])
    if action == "explain":
        return ["explain"]
    argv = [action]
    if action in ("score", "better"):
        argv.append(_ask("\nBarcode (digits under the barcode) or product name"))
    elif action == "find":
        argv.append(_ask("\nWhat are you looking for? (e.g. organic chickpeas)"))
    else:
        print("\nSome categories: " + ", ".join(sorted(SHORTCUTS)[:24]) + ", ...")
        argv.append(_ask("Category", "oats"))

    country = _ask("\nWhich country do you shop in? (e.g. canada, united-states, united-kingdom; blank = anywhere)")
    store = _ask("Which store? (e.g. costco, walmart, loblaws, tesco; blank = any store)")
    if country:
        argv += ["--country", country.lower().replace(" ", "-")]
    if store:
        argv += ["--store", store.lower().replace(" ", "-")]

    diet = _choose("Any diet needs?", [
        ("No restrictions", ""), ("Halal-friendly (certified, or plant/egg/dairy with no haram ingredients)", "halal"),
        ("Halal certified only", "halal-strict"), ("No pork", "no-pork"), ("No pork and no beef", "no-pork,no-beef"),
        ("Vegetarian", "vegetarian"), ("Vegan", "vegan")])
    if diet:
        argv += ["--diet", diet]

    if action != "score":
        bar = _choose("How picky should I be?", [
            ("Excellent only (90+)", ("--band", "excellent")), ("Very good and up (75+)", ("--band", "very-good")),
            ("Good and up (50+)", ("--band", "good")), ("Show everything", None), ("Let me type my own minimum", "own")])
        if bar == "own":
            n = _ask("Minimum score 0-100", "90")
            argv += ["--min", n if n.isdigit() else "90"]
        elif bar:
            argv += list(bar)
        if _ask("\nOrganic only? (y/n)", "n").lower().startswith("y"):
            argv.append("--organic")
        if _ask("Save a printable shopping list with photos? (y/n)", "y").lower().startswith("y"):
            argv += ["--report", _ask("File name", "betty-list.html")]
    print("\nSearching Open Food Facts (it's polite to go slowly, so this can take a few seconds)...")
    return argv
