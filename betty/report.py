"""Printable HTML shopping list (open it, then Print -> Save as PDF)."""
import html, datetime

COLORS = {"Excellent": "#1a7f45", "Very good": "#3fa34d", "Good": "#8bbf3a", "Bad": "#e08a1e", "Very bad": "#d14343"}
GUIDE = ("<b>Guide only.</b> Betty is a helpful guide, not a guarantee. Always read the label yourself to confirm "
         "ingredients, allergens and certifications. What you buy and eat is your own decision and at your own discretion.")


def write_html(path, results, title):
    e = html.escape
    cards = []
    for r in results:
        img = f'<img src="{e(r["image"])}" alt="">' if r.get("image") else '<div class="noimg">no photo</div>'
        cards.append(f"""
<div class="card">{img}
 <div class="body"><b>{e(r.get('name') or '?')}</b><br>
  <span class="muted">{e(r.get('brands') or '')} {e(r.get('quantity') or '')}</span><br>
  {'<span class="chip org">Organic</span>' if r['organic'] else ''}
  {''.join(f'<span class="chip">{e(b)}</span>' for b in r.get('fits', []))}
  {''.join(f'<span class="chip {"note" if w.startswith("halal: check") else "warn"}">{e(w)}</span>' for w in r.get('warnings', []))}<br>
  <span class="muted">Nutrition {r['nutrition_rating']}/100 &middot; Additives {r['additive_rating']}/100
  {(' &middot; check ' + e(', '.join(x.upper() for x in r['flagged_additives']))) if r['flagged_additives'] else ''}</span><br>
  <a href="{e(r['url'])}">Open Food Facts page</a> &middot; barcode {e(r.get('code') or '')}
 </div>
 <div class="score" style="background:{COLORS.get(r['label'], '#888')}">{r['score']}<small>{e(r['label'])}</small></div>
</div>""")
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{e(title)}</title>
<style>
body{{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:24px;color:#1d2a24;background:#fff}}
h1{{font-size:22px;margin:0 0 4px}} .muted{{color:#5b6b63;font-size:12px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:10px;margin-top:14px}}
.card{{display:flex;gap:10px;border:1px solid #d5e2da;border-radius:10px;padding:8px;break-inside:avoid}}
.card img,.noimg{{width:84px;height:84px;object-fit:contain;flex:none}} .noimg{{background:#f2f2f2;font-size:11px;
display:flex;align-items:center;justify-content:center;color:#888}}
.body{{flex:1;font-size:13px;line-height:1.35}} .chip{{display:inline-block;background:#eef5f0;border-radius:6px;
padding:1px 6px;margin:2px 4px 2px 0;font-size:11px}} .chip.org{{background:#dff1e5;font-weight:600}}
.chip.warn{{background:#fdecea;color:#a12d2d}} .chip.note{{background:#fff7ec;border:1px solid #e08a1e}} .guide{{margin-top:12px;padding:8px 12px;border-left:4px solid #e08a1e;
background:#fff7ec;font-size:13px}}
.score{{flex:none;width:58px;height:58px;border-radius:10px;color:#fff;font-weight:700;font-size:22px;
display:flex;flex-direction:column;align-items:center;justify-content:center}} .score small{{font-size:9px;font-weight:500}}
footer{{margin-top:18px;font-size:11px;color:#5b6b63}} @media print{{body{{margin:8mm}} a{{color:inherit}}}}
</style></head><body>
<h1>{e(title)}</h1><div class="muted">{len(results)} products &middot; made {datetime.date.today():%B %d, %Y} with Betty Better Eater</div>
<div class="guide">{GUIDE}</div>
<div class="grid">{''.join(cards)}</div>
<footer>Scores are independent estimates based on Yuka's published method (not official Yuka scores). Product data and
photos: <a href="https://world.openfoodfacts.org">Open Food Facts</a> contributors, data under ODbL, photos under CC BY-SA.
Recipes change and crowd-sourced data can be wrong or incomplete. Not medical, allergy or religious advice.</footer>
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
