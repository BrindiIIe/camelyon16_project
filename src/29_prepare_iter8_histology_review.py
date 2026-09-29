"""Build a self-contained histology review pack for the three iter8 regressions.

This script only reads validation slides and existing iter7/iter8 probabilities.
It never copies validation patches into a training dataset.
"""

from __future__ import annotations

from pathlib import Path
import csv
import html
import json
import os
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib_cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.path import Path as PolygonPath
import numpy as np
import openslide


TARGET_SLIDES = ("tumor_071", "tumor_074", "tumor_096")
OUT = ROOT / "portable_review_packs" / "iter8_targeted_histology_review"
IMAGES = OUT / "images"
OVERVIEWS = OUT / "overviews"
PATCH_SIZE = 256
CONTEXT_SIZE = 2048
ZOOM_SIZE = 768
LOST_PER_SLIDE = 10
CONTROL_PER_SLIDE = 2
MIN_DISTANCE = 1536.0


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def parse_annotations(path: Path) -> dict[str, list[np.ndarray]]:
    result: dict[str, list[np.ndarray]] = {"Tumor": [], "Exclusion": []}
    for annotation in ET.parse(path).iter("Annotation"):
        group = annotation.get("PartOfGroup")
        if group not in result:
            raise ValueError(f"Unknown annotation group {group!r} in {path}")
        coordinates = sorted(
            annotation.findall("./Coordinates/Coordinate"),
            key=lambda coordinate: int(coordinate.get("Order", "0")),
        )
        points = np.array(
            [(float(c.get("X")), float(c.get("Y"))) for c in coordinates],
            dtype=np.float64,
        )
        if len(points) < 3:
            raise ValueError(f"Invalid polygon in {path}")
        result[group].append(points)
    if not result["Tumor"]:
        raise ValueError(f"No tumor polygon in {path}")
    return result


def inside_annotations(xy: np.ndarray, regions: dict[str, list[np.ndarray]]) -> np.ndarray:
    masks: dict[str, np.ndarray] = {}
    for group, shapes in regions.items():
        mask = np.zeros(len(xy), dtype=bool)
        for shape in shapes:
            candidate = np.flatnonzero(
                np.all((xy >= shape.min(axis=0)) & (xy <= shape.max(axis=0)), axis=1)
            )
            mask[candidate] |= PolygonPath(shape).contains_points(xy[candidate])
        masks[group] = mask
    return masks["Tumor"] & ~masks["Exclusion"]


def spaced_selection(
    indices: np.ndarray,
    score: np.ndarray,
    xy: np.ndarray,
    count: int,
    blocked: set[int] | None = None,
) -> list[int]:
    """Greedily retain high-score sites while spreading the histology review."""
    chosen: list[int] = []
    blocked = set() if blocked is None else set(blocked)
    ordered = indices[np.argsort(score[indices])[::-1]]
    for distance in (MIN_DISTANCE, MIN_DISTANCE / 2, 0):
        for idx in ordered:
            idx = int(idx)
            if idx in blocked or idx in chosen:
                continue
            if distance and any(np.linalg.norm(xy[idx] - xy[other]) < distance for other in chosen):
                continue
            chosen.append(idx)
            if len(chosen) == count:
                return chosen
    if len(chosen) != count:
        raise RuntimeError(f"Could select only {len(chosen)}/{count} candidates")
    return chosen


def read_region_centered(slide: openslide.OpenSlide, x: int, y: int, size: int):
    half = size // 2
    return slide.read_region((x - half, y - half), 0, (size, size)).convert("RGB")


def draw_annotation_overlay(ax, regions, x0, y0, size):
    for group, shapes in regions.items():
        color = "#e31a1c" if group == "Tumor" else "#ff8c00"
        for shape in shapes:
            if (
                shape[:, 0].max() < x0
                or shape[:, 0].min() > x0 + size
                or shape[:, 1].max() < y0
                or shape[:, 1].min() > y0 + size
            ):
                continue
            closed = np.vstack([shape, shape[0]])
            ax.plot(closed[:, 0], closed[:, 1], color=color, linewidth=1.3)


def make_candidate_sheet(slide, regions, row, destination: Path):
    x, y = int(row["x"]), int(row["y"])
    context = read_region_centered(slide, x, y, CONTEXT_SIZE)
    zoom = read_region_centered(slide, x, y, ZOOM_SIZE)
    patch = read_region_centered(slide, x, y, PATCH_SIZE)

    fig = plt.figure(figsize=(15.5, 8.2), constrained_layout=True)
    grid = fig.add_gridspec(2, 3, width_ratios=(1.55, 1, 0.85), height_ratios=(1, 1))
    context_ax = fig.add_subplot(grid[:, 0])
    zoom_ax = fig.add_subplot(grid[0, 1])
    patch_ax = fig.add_subplot(grid[1, 1])
    text_ax = fig.add_subplot(grid[:, 2])

    x0, y0 = x - CONTEXT_SIZE // 2, y - CONTEXT_SIZE // 2
    context_ax.imshow(context, extent=(x0, x0 + CONTEXT_SIZE, y0 + CONTEXT_SIZE, y0))
    draw_annotation_overlay(context_ax, regions, x0, y0, CONTEXT_SIZE)
    context_ax.add_patch(
        Rectangle((x - PATCH_SIZE // 2, y - PATCH_SIZE // 2), PATCH_SIZE, PATCH_SIZE,
                  fill=False, edgecolor="#00ffff", linewidth=1.8)
    )
    context_ax.set_title("Contexte 2048 px — rouge: tumeur XML, cyan: patch exact")
    context_ax.set_xlim(x0, x0 + CONTEXT_SIZE)
    context_ax.set_ylim(y0 + CONTEXT_SIZE, y0)
    context_ax.set_aspect("equal")

    zoom_ax.imshow(zoom)
    zoom_ax.add_patch(
        Rectangle(((ZOOM_SIZE - PATCH_SIZE) / 2, (ZOOM_SIZE - PATCH_SIZE) / 2),
                  PATCH_SIZE, PATCH_SIZE, fill=False, edgecolor="#00ffff", linewidth=1.8)
    )
    zoom_ax.set_title("Zoom 768 px")
    zoom_ax.axis("off")

    patch_ax.imshow(patch)
    patch_ax.set_title("Patch exact vu par le modèle — 256 px")
    patch_ax.axis("off")

    text_ax.axis("off")
    text_ax.text(
        0.02,
        0.98,
        "\n".join(
            [
                row["candidate_id"],
                "",
                f"Lame : {row['slide_id']}",
                f"Centre niveau 0 : ({x}, {y})",
                f"Sélection : {row['selection_reason']}",
                "",
                f"P(tumeur) Iter7 : {float(row['iter7_prob']):.4f}",
                f"P(tumeur) Iter8 : {float(row['iter8_prob']):.4f}",
                f"Chute Iter7−Iter8 : {float(row['probability_drop']):.4f}",
                "",
                "Questions de revue :",
                "1. Le centre contient-il de la tumeur ?",
                "2. Quel motif histologique domine ?",
                "3. Quelle cause explique la perte de signal ?",
                "4. Ce motif doit-il guider l'expérience Iter9 ?",
                "",
                "Validation uniquement — ne pas intégrer au train.",
            ]
        ),
        va="top",
        fontsize=11,
        linespacing=1.45,
    )
    fig.suptitle(f"Revue histologique ciblée Iter8 — {row['candidate_id']}", fontsize=15)
    fig.savefig(destination, dpi=130, facecolor="white")
    plt.close(fig)


def make_overview(slide, regions, candidates, destination: Path):
    width, height = slide.dimensions
    thumbnail = slide.get_thumbnail((1500, 1100)).convert("RGB")
    sx, sy = thumbnail.width / width, thumbnail.height / height
    fig, ax = plt.subplots(figsize=(14, 9), constrained_layout=True)
    ax.imshow(thumbnail)
    for group, shapes in regions.items():
        color = "#e31a1c" if group == "Tumor" else "#ff8c00"
        for shape in shapes:
            closed = np.vstack([shape, shape[0]])
            ax.plot(closed[:, 0] * sx, closed[:, 1] * sy, color=color, linewidth=1.1)
    for row in candidates:
        x, y = int(row["x"]) * sx, int(row["y"]) * sy
        label = row["candidate_id"].split("_")[-1]
        ax.scatter([x], [y], s=35, facecolor="#00ffff", edgecolor="black", linewidth=0.7)
        ax.text(x + 5, y - 5, label, fontsize=8, weight="bold", color="black",
                bbox=dict(facecolor="white", alpha=0.75, edgecolor="none", pad=1))
    ax.set_title(f"{candidates[0]['slide_id']} — sites de revue (rouge: tumeur XML)")
    ax.axis("off")
    fig.savefig(destination, dpi=140, facecolor="white")
    plt.close(fig)


def csv_fieldnames() -> list[str]:
    return [
        "candidate_id", "slide_id", "x", "y", "selection_reason",
        "iter7_prob", "iter8_prob", "probability_drop", "image",
        "tumor_at_center", "dominant_pattern", "likely_failure_mechanism",
        "iter9_priority", "reviewer", "review_date", "notes",
    ]


def write_csv(path: Path, rows: list[dict[str, str]]):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=csv_fieldnames())
        writer.writeheader()
        writer.writerows(rows)


def build_html(rows: list[dict[str, str]]):
    payload = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    overview_html = "".join(
        f'<section><h2>{slide}</h2><img class="overview" src="overviews/{slide}.jpg" alt="Vue d’ensemble {slide}"></section>'
        for slide in TARGET_SLIDES
    )
    document = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Revue histologique ciblée Iter8</title>
<style>
body{{font-family:system-ui,sans-serif;margin:0;background:#f4f5f7;color:#1c2430}}header{{position:sticky;top:0;background:#17212b;color:white;padding:14px 24px;z-index:2;box-shadow:0 2px 8px #0004}}main{{max-width:1500px;margin:auto;padding:20px}}button{{padding:9px 14px;margin-right:8px;font-weight:650;cursor:pointer}}.warning{{background:#fff4ce;border-left:5px solid #f0ad00;padding:12px}}.overview{{max-width:100%;border:1px solid #aaa;background:white}}.card{{background:white;margin:22px 0;padding:16px;border-radius:8px;box-shadow:0 2px 8px #0002}}.sheet{{width:100%;max-height:82vh;object-fit:contain;background:#eee}}.fields{{display:grid;grid-template-columns:repeat(4,minmax(180px,1fr));gap:12px;margin-top:12px}}label{{font-size:.88rem;font-weight:650}}select,input,textarea{{display:block;width:100%;box-sizing:border-box;margin-top:4px;padding:7px}}textarea{{min-height:70px}}.meta{{font-family:ui-monospace,monospace;color:#344;font-size:.9rem}}@media(max-width:900px){{.fields{{grid-template-columns:1fr 1fr}}}}
</style></head><body>
<header><strong>Revue histologique ciblée Iter8</strong> — <span id="progress">0/36 renseignés</span> <button onclick="exportCsv()">Exporter le CSV</button><button onclick="clearReview()">Effacer la saisie</button></header>
<main><p class="warning"><strong>Données de validation.</strong> Ce pack sert au diagnostic et à la conception de l’expérience suivante. Aucun patch présenté ici ne doit être ajouté à l’entraînement.</p>
<p>Pour chaque site, examiner le contexte, le zoom et le patch exact. Les réponses sont conservées localement dans ce navigateur. Utiliser « Exporter le CSV » à la fin.</p>
{overview_html}<div id="cards"></div></main>
<script>
const rows={payload}; const key='iter8_targeted_histology_review_v1'; let state=JSON.parse(localStorage.getItem(key)||'{{}}');
const options={{tumor_at_center:['','yes','no','uncertain'],dominant_pattern:['','cohesive_metastasis','small_clusters','isolated_tumor_cells','low_tumor_fraction','fibrosis_desmoplasia','necrosis','crush_or_processing_artifact','annotation_edge','other','uncertain'],likely_failure_mechanism:['','subtle_tumor_morphology','low_tumor_fraction','fibrosis_or_desmoplasia','necrosis','artifact','stain_or_color_shift','annotation_or_sampling','class_exposure_shift','unclear'],iter9_priority:['','high','medium','low','exclude']}};
function esc(s){{return String(s??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]))}}
function select(name,id){{return `<label>${{name.replaceAll('_',' ')}}<select data-id="${{id}}" data-field="${{name}}">${{options[name].map(x=>`<option value="${{x}}" ${{(state[id]?.[name]||'')===x?'selected':''}}>${{x||'— choisir —'}}</option>`).join('')}}</select></label>`}}
const cards=document.getElementById('cards'); rows.forEach(r=>{{let id=r.candidate_id,s=state[id]||{{}};cards.insertAdjacentHTML('beforeend',`<article class="card"><h2>${{esc(id)}}</h2><p class="meta">${{esc(r.slide_id)}} · centre (${{r.x}}, ${{r.y}}) · ${{esc(r.selection_reason)}} · Iter7=${{Number(r.iter7_prob).toFixed(4)}} · Iter8=${{Number(r.iter8_prob).toFixed(4)}}</p><img class="sheet" loading="lazy" src="${{esc(r.image)}}" alt="${{esc(id)}}"><div class="fields">${{select('tumor_at_center',id)}}${{select('dominant_pattern',id)}}${{select('likely_failure_mechanism',id)}}${{select('iter9_priority',id)}}<label>reviewer<input data-id="${{id}}" data-field="reviewer" value="${{esc(s.reviewer||'')}}"></label><label>review date<input type="date" data-id="${{id}}" data-field="review_date" value="${{esc(s.review_date||'')}}"></label><label style="grid-column:span 2">notes<textarea data-id="${{id}}" data-field="notes">${{esc(s.notes||'')}}</textarea></label></div></article>`);}});
document.addEventListener('input',e=>{{let id=e.target.dataset.id;if(!id)return;state[id]=state[id]||{{}};state[id][e.target.dataset.field]=e.target.value;localStorage.setItem(key,JSON.stringify(state));progress();}});
function progress(){{let n=rows.filter(r=>state[r.candidate_id]?.tumor_at_center).length;document.getElementById('progress').textContent=`${{n}}/${{rows.length}} renseignés`;}}progress();
function csvCell(v){{v=String(v??'');let quote=v.includes(',')||v.includes('"')||v.includes(String.fromCharCode(10))||v.includes(String.fromCharCode(13));return quote?'"'+v.replaceAll('"','""')+'"':v}}
function exportCsv(){{const fields={json.dumps(csv_fieldnames(), ensure_ascii=False)};let lines=[fields.join(',')];for(const r of rows){{const s=state[r.candidate_id]||{{}};lines.push(fields.map(f=>csvCell(s[f]??r[f]??'')).join(','));}}let blob=new Blob([String.fromCharCode(0xfeff)+lines.join(String.fromCharCode(13,10))],{{type:'text/csv;charset=utf-8'}}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='review_completed.csv';a.click();URL.revokeObjectURL(a.href);}}
function clearReview(){{if(confirm('Effacer toute la saisie locale ?')){{localStorage.removeItem(key);location.reload();}}}}
</script></body></html>"""
    (OUT / "review.html").write_text(document, encoding="utf-8", newline="\n")


def write_readme(rows: list[dict[str, str]]):
    counts = {slide: sum(row["slide_id"] == slide for row in rows) for slide in TARGET_SLIDES}
    text = f"""# Revue histologique ciblée Iter8

Ce pack documente la perte de signal localisée entre Iter7 et Iter8 sur
`tumor_071`, `tumor_074` et `tumor_096`. Il contient {len(rows)} sites de revue
({', '.join(f'{slide}: {count}' for slide, count in counts.items())}).

## Utilisation

1. Ouvrir `review.html` dans Chrome, Edge ou Firefox.
2. Examiner d'abord la vue d'ensemble de la lame, puis chaque planche.
3. Renseigner les quatre décisions et, si nécessaire, les notes.
4. Cliquer sur **Exporter le CSV**. Le fichier téléchargé est
   `review_completed.csv`.

La saisie intermédiaire est conservée dans le stockage local du navigateur.
`review_template.csv` contient les mêmes sites avec des colonnes vierges si une
revue dans un tableur est préférable.

## Échantillonnage

Pour chaque lame, dix sites tumoraux annotés sont choisis parmi les plus fortes
chutes de probabilité Iter7→Iter8, avec espacement spatial. Deux sites
supplémentaires correspondent au meilleur signal Iter8 restant et servent de
contrôles internes. Le carré cyan indique le patch exact de 256 px vu par le
modèle. Les contours rouges sont les annotations Tumor et les contours orange
les Exclusion.

## Garde-fou expérimental

Ces trois lames appartiennent à la validation. Les images du pack servent
uniquement à comprendre l'échec et à définir une expérience sur les données
d'entraînement. Elles ne doivent jamais être copiées dans un dataset de train.
Le jeu `test_final` n'est pas utilisé.
"""
    (OUT / "README_REVIEW.md").write_text(text, encoding="utf-8", newline="\n")


def main():
    # Replace generated image assets while preserving any completed review CSV
    # that a reviewer may have saved alongside the pack.
    for generated_directory in (IMAGES, OVERVIEWS):
        if generated_directory.exists():
            shutil.rmtree(generated_directory)
    IMAGES.mkdir(parents=True)
    OVERVIEWS.mkdir(parents=True)
    all_rows: list[dict[str, str]] = []

    for slide_id in TARGET_SLIDES:
        regions = parse_annotations(ROOT / "data" / "annotations" / f"{slide_id}.xml")
        iter7 = read_csv(ROOT / "data" / "inference_iter7_val" / f"{slide_id}_probs.csv")
        iter8 = read_csv(ROOT / "data" / "inference_iter8_val" / f"{slide_id}_probs.csv")
        xy = np.array([(int(row["x"]), int(row["y"])) for row in iter7], dtype=np.int64)
        xy8 = np.array([(int(row["x"]), int(row["y"])) for row in iter8], dtype=np.int64)
        if not np.array_equal(xy, xy8):
            raise ValueError(f"Grid mismatch for {slide_id}")
        p7 = np.array([float(row["prob_tumor"]) for row in iter7])
        p8 = np.array([float(row["prob_tumor"]) for row in iter8])
        inside = inside_annotations(xy, regions)
        lost_pool = np.flatnonzero(inside & (p7 >= 0.5) & (p8 < 0.5))
        lost = spaced_selection(lost_pool, p7 - p8, xy, LOST_PER_SLIDE)
        control_pool = np.flatnonzero(inside)
        controls = spaced_selection(control_pool, p8, xy, CONTROL_PER_SLIDE, set(lost))
        selected = [(idx, "largest_iter7_to_iter8_drop") for idx in lost]
        selected += [(idx, "highest_remaining_iter8_signal") for idx in controls]

        slide_rows: list[dict[str, str]] = []
        with openslide.OpenSlide(str(ROOT / "data" / "wsi" / f"{slide_id}.tif")) as slide:
            for rank, (idx, reason) in enumerate(selected, start=1):
                candidate_id = f"{slide_id}_site_{rank:02d}"
                row = {
                    "candidate_id": candidate_id,
                    "slide_id": slide_id,
                    "x": str(int(xy[idx, 0])),
                    "y": str(int(xy[idx, 1])),
                    "selection_reason": reason,
                    "iter7_prob": f"{p7[idx]:.8f}",
                    "iter8_prob": f"{p8[idx]:.8f}",
                    "probability_drop": f"{p7[idx] - p8[idx]:.8f}",
                    "image": f"images/{candidate_id}.jpg",
                    "tumor_at_center": "",
                    "dominant_pattern": "",
                    "likely_failure_mechanism": "",
                    "iter9_priority": "",
                    "reviewer": "",
                    "review_date": "",
                    "notes": "",
                }
                make_candidate_sheet(slide, regions, row, IMAGES / f"{candidate_id}.jpg")
                slide_rows.append(row)
                all_rows.append(row)
                print(f"Created {candidate_id}", flush=True)
            make_overview(slide, regions, slide_rows, OVERVIEWS / f"{slide_id}.jpg")

    write_csv(OUT / "review_template.csv", all_rows)
    build_html(all_rows)
    write_readme(all_rows)
    print(f"Review pack ready: {OUT}")


if __name__ == "__main__":
    main()
