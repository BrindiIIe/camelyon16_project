"""Build the portable Iter9 hard-positive histology review pack."""

from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import openslide
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = ROOT / "outputs" / "iter9_hard_positive_mining" / "candidates.csv"
STATUS_JSON = ROOT / "outputs" / "iter9_hard_positive_mining" / "status.json"
SPLIT_CSV = ROOT / "outputs" / "splits" / "wsi_split_v1.csv"
OUT = ROOT / "portable_review_packs" / "iter9_hard_positive_review"
IMAGES = OUT / "images"
PATCHES = OUT / "patches"
WSI_DIR = ROOT / "data" / "wsi"
ANNOTATION_DIR = ROOT / "data" / "annotations"

PATCH_SIZE = 256
ZOOM_SIZE = 768
CONTEXT_SIZE = 1536
PANEL_SIZE = 768

METADATA_FIELDS = [
    "candidate_id", "slide_id", "x", "y", "iter8_prob", "nonwhite_ratio",
    "selection_rank_within_slide", "patch_path", "review_image",
]
REVIEW_FIELDS = [
    "review_role", "review_status", "site_diagnosis", "dominant_pattern",
    "image_quality", "confidence", "include_as_hard_positive", "reviewer",
    "review_date", "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def parse_annotations(path: Path) -> dict[str, list[list[tuple[float, float]]]]:
    regions: dict[str, list[list[tuple[float, float]]]] = {"Tumor": [], "Exclusion": []}
    for annotation in ET.parse(path).iter("Annotation"):
        group = annotation.get("PartOfGroup")
        if group not in regions:
            raise ValueError(f"Unknown annotation group {group!r} in {path}")
        coordinates = sorted(
            annotation.findall("./Coordinates/Coordinate"),
            key=lambda coordinate: int(coordinate.get("Order", "0")),
        )
        points = [
            (float(coordinate.get("X")), float(coordinate.get("Y")))
            for coordinate in coordinates
        ]
        if len(points) < 3:
            raise ValueError(f"Invalid polygon in {path}")
        regions[group].append(points)
    return regions


def centered_region(slide: openslide.OpenSlide, x: int, y: int, size: int) -> Image.Image:
    half = size // 2
    return slide.read_region((x - half, y - half), 0, (size, size)).convert("RGB")


def add_context_overlay(
    image: Image.Image,
    regions: dict[str, list[list[tuple[float, float]]]],
    x: int,
    y: int,
) -> Image.Image:
    draw = ImageDraw.Draw(image)
    x0, y0 = x - CONTEXT_SIZE // 2, y - CONTEXT_SIZE // 2
    for group, polygons in regions.items():
        color = "#e31a1c" if group == "Tumor" else "#ff8c00"
        for polygon in polygons:
            local = [(px - x0, py - y0) for px, py in polygon]
            draw.line(local + [local[0]], fill=color, width=5)
    half = PATCH_SIZE // 2
    draw.rectangle(
        (CONTEXT_SIZE // 2 - half, CONTEXT_SIZE // 2 - half,
         CONTEXT_SIZE // 2 + half, CONTEXT_SIZE // 2 + half),
        outline="#00ffff", width=6,
    )
    return image


def labelled_panel(image: Image.Image, label: str) -> Image.Image:
    panel = Image.new("RGB", (PANEL_SIZE, PANEL_SIZE + 42), "white")
    panel.paste(image.resize((PANEL_SIZE, PANEL_SIZE), Image.Resampling.LANCZOS), (0, 42))
    ImageDraw.Draw(panel).text((12, 12), label, fill="#17212b", font=ImageFont.load_default())
    return panel


def make_assets(
    slide: openslide.OpenSlide,
    regions: dict[str, list[list[tuple[float, float]]]],
    row: dict[str, str],
) -> None:
    x, y = int(row["x"]), int(row["y"])
    context = add_context_overlay(centered_region(slide, x, y, CONTEXT_SIZE), regions, x, y)
    zoom = centered_region(slide, x, y, ZOOM_SIZE)
    zoom_draw = ImageDraw.Draw(zoom)
    border = (ZOOM_SIZE - PATCH_SIZE) // 2
    zoom_draw.rectangle((border, border, border + PATCH_SIZE, border + PATCH_SIZE), outline="#00ffff", width=4)
    patch = centered_region(slide, x, y, PATCH_SIZE)

    sheet = Image.new("RGB", (PANEL_SIZE * 3, PANEL_SIZE + 42), "white")
    for index, panel in enumerate(
        (
            labelled_panel(context, "Contexte 1536 px - rouge: tumeur, cyan: patch"),
            labelled_panel(zoom, "Zoom 768 px - cyan: patch exact"),
            labelled_panel(patch, "Patch exact 256 px vu par le modele"),
        )
    ):
        sheet.paste(panel, (index * PANEL_SIZE, 0))
    sheet.save(IMAGES / f"{row['candidate_id']}.jpg", quality=88, optimize=True)
    patch.save(PATCHES / f"{row['candidate_id']}.png", optimize=True)


def validate_and_prepare_rows() -> list[dict[str, str]]:
    status = json.loads(STATUS_JSON.read_text(encoding="utf-8"))
    if status.get("state") != "complete" or status.get("processed_slides") != 86:
        raise ValueError("The 86 training tumor WSI must be fully mined first.")
    split = {row["slide_id"]: row for row in read_csv(SPLIT_CSV)}
    source = read_csv(SOURCE_CSV)
    if not source or len(source) > 120:
        raise ValueError(f"Unexpected candidate count: {len(source)}")
    identifiers: set[str] = set()
    coordinates: set[tuple[str, str, str]] = set()
    rows: list[dict[str, str]] = []
    for item in source:
        slide_id = item["slide_id"]
        if split.get(slide_id, {}).get("split") != "train" or split[slide_id].get("label") != "tumor":
            raise ValueError(f"Candidate outside training tumor WSI: {slide_id}")
        identity = item["candidate_id"]
        coordinate = (slide_id, item["x"], item["y"])
        if identity in identifiers or coordinate in coordinates:
            raise ValueError(f"Duplicate candidate: {identity} {coordinate}")
        identifiers.add(identity)
        coordinates.add(coordinate)
        row = {field: item.get(field, "") for field in METADATA_FIELDS}
        row["patch_path"] = f"patches/{identity}.png"
        row["review_image"] = f"images/{identity}.jpg"
        row.update(
            review_role="junior",
            review_status="independent_preliminary",
            site_diagnosis="",
            dominant_pattern="",
            image_quality="",
            confidence="",
            include_as_hard_positive="",
            reviewer="",
            review_date="",
            notes="",
        )
        rows.append(row)
    return rows


def write_template(rows: list[dict[str, str]]) -> None:
    with (OUT / "review_template.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=METADATA_FIELDS + REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_html(rows: list[dict[str, str]]) -> None:
    payload = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    fields = json.dumps(METADATA_FIELDS + REVIEW_FIELDS, ensure_ascii=False)
    template = r'''<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Revue des hard positives Iter9</title><style>
:root{--navy:#17324d;--green:#18794e;--red:#b42318;--border:#c8d2dc}*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;margin:0;background:#f3f5f7;color:#17212b}header{position:sticky;top:0;z-index:5;background:var(--navy);color:#fff;padding:12px 20px;box-shadow:0 2px 9px #0005}.head{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.title{font-weight:750;margin-right:auto}button{border:1px solid #ffffff55;background:#fff;color:var(--navy);border-radius:5px;padding:8px 12px;font-weight:700;cursor:pointer}.danger{background:transparent;color:#fff;border-color:#ffb4ab}.global{display:grid;grid-template-columns:minmax(210px,1fr) 170px;gap:10px;margin-top:10px;max-width:620px}header label{font-size:.78rem;font-weight:700}header input{display:block;width:100%;margin-top:3px;padding:7px;border:0;border-radius:4px}
main{max-width:1500px;margin:auto;padding:18px}.info{background:#eaf4fb;border-left:5px solid #24577f;padding:12px 14px}.card{background:#fff;margin:22px 0;padding:16px;border-radius:8px;box-shadow:0 2px 8px #0002;border-left:6px solid #aab5bf;scroll-margin-top:145px}.card.complete{border-left-color:var(--green)}.card h2{margin:0 0 5px}.status{font-size:.85rem;font-weight:750;color:#5f6b76}.complete .status{color:var(--green)}.sheet{display:block;width:100%;max-height:78vh;object-fit:contain;background:#eee;margin-top:10px}.fields{display:grid;grid-template-columns:repeat(3,minmax(210px,1fr));gap:12px;margin-top:14px}.fields label{font-size:.88rem;font-weight:700}.required::after{content:' *';color:var(--red)}select,textarea{display:block;width:100%;margin-top:4px;padding:8px;border:1px solid #aab5bf;border-radius:4px;background:#fff}textarea{min-height:82px}.model-info{font-family:ui-monospace,monospace;font-size:.86rem;color:#344}@media(max-width:900px){header{position:static}.global,.fields{grid-template-columns:1fr}.card{scroll-margin-top:10px}}
</style></head><body><header><div class="head"><span class="title">Revue des hard positives Iter9</span><span id="progress"></span><button onclick="nextIncomplete()">Prochain incomplet</button><button onclick="exportCsv()">Exporter le CSV</button><button class="danger" onclick="clearReview()">Effacer</button></div><div class="global"><label>Nom ou initiales<input id="reviewer" placeholder="obligatoire pour l'export"></label><label>Date de lecture<input id="reviewDate" type="date"></label></div></header>
<main><p class="info"><strong>Données d’entraînement uniquement.</strong> Chaque site est situé au cœur d’une annotation tumorale mais a reçu une probabilité Iter8 inférieure à 0,25. Confirmez l’histologie avant toute inclusion. La saisie est enregistrée automatiquement dans ce navigateur.</p><p>Inclure seulement un patch où la tumeur est confirmée, l’image est interprétable, la confiance est moyenne ou élevée et le motif dominant n’est pas un bord d’annotation. Les informations du modèle sont repliées pour limiter le biais de lecture.</p><div id="cards"></div></main>
<script>const rows=__ROWS__;const fields=__FIELDS__;const key='iter9_hard_positive_review_v1';const stored=JSON.parse(localStorage.getItem(key)||'{}');let state=stored.rows||{};const globalState=stored.global||{};const required=['site_diagnosis','dominant_pattern','image_quality','confidence','include_as_hard_positive'];
const choices={site_diagnosis:[['','— choisir —'],['tumor','Tumeur présente'],['benign','Tissu bénin'],['uncertain','Incertain'],['non_evaluable','Non évaluable']],dominant_pattern:[['','— choisir —'],['cohesive_metastasis','Métastase cohésive'],['small_tumor_clusters','Petits amas tumoraux'],['isolated_tumor_cells','Cellules tumorales isolées'],['low_tumor_fraction','Faible proportion tumorale'],['tumor_in_fibrosis_or_desmoplasia','Tumeur dans fibrose/desmoplasie'],['tumor_in_necrosis','Tumeur dans nécrose'],['benign_lymphoid_tissue','Tissu lymphoïde bénin'],['sinus_histiocytosis','Histiocytose sinusale'],['processing_artifact','Artefact de préparation'],['annotation_edge','Bord d’annotation'],['other','Autre'],['uncertain','Incertain']],image_quality:[['','— choisir —'],['good','Bonne'],['interpretable_with_limitations','Interprétable avec limites'],['non_evaluable','Non évaluable']],confidence:[['','— choisir —'],['high','Élevée'],['medium','Moyenne'],['low','Faible']],include_as_hard_positive:[['','— choisir —'],['yes','Oui, inclure'],['no','Non, exclure']]};
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}function select(field,id,label){const value=state[id]?.[field]||'';return `<label><span class="required">${esc(label)}</span><select data-id="${esc(id)}" data-field="${field}">${choices[field].map(([code,text])=>`<option value="${esc(code)}" ${value===code?'selected':''}>${esc(text)}</option>`).join('')}</select></label>`}function complete(id){return required.every(field=>Boolean(state[id]?.[field]))}
function render(){const cards=document.getElementById('cards');cards.innerHTML='';rows.forEach((row,index)=>{const id=row.candidate_id;const done=complete(id);cards.insertAdjacentHTML('beforeend',`<article class="card ${done?'complete':''}" id="card-${esc(id)}"><h2>${index+1}/${rows.length} — ${esc(id)}</h2><div class="status">${done?'Complet':'À compléter'}</div><img class="sheet" loading="lazy" src="${esc(row.review_image)}" alt="${esc(id)}"><details><summary>Informations techniques</summary><p class="model-info">${esc(row.slide_id)} · centre (${esc(row.x)}, ${esc(row.y)}) · rang ${esc(row.selection_rank_within_slide)} · P(tumeur) Iter8=${Number(row.iter8_prob).toFixed(5)} · tissu=${(100*Number(row.nonwhite_ratio)).toFixed(1)} %</p></details><div class="fields">${select('site_diagnosis',id,'Diagnostic du patch central')}${select('dominant_pattern',id,'Motif histologique dominant')}${select('image_quality',id,'Qualité de l’image')}${select('confidence',id,'Niveau de confiance')}${select('include_as_hard_positive',id,'Inclure dans Iter9')}<label>Commentaire<textarea data-id="${esc(id)}" data-field="notes">${esc(state[id]?.notes||'')}</textarea></label></div></article>`)});progress()}
function save(){globalState.reviewer=document.getElementById('reviewer').value.trim();globalState.review_date=document.getElementById('reviewDate').value;localStorage.setItem(key,JSON.stringify({rows:state,global:globalState}))}function progress(){const n=rows.filter(row=>complete(row.candidate_id)).length;document.getElementById('progress').textContent=`${n}/${rows.length} complets`;document.querySelectorAll('.card').forEach(card=>{const id=card.id.replace('card-','');const done=complete(id);card.classList.toggle('complete',done);card.querySelector('.status').textContent=done?'Complet':'À compléter'})}
document.addEventListener('input',event=>{const id=event.target.dataset.id;if(id){state[id]=state[id]||{};state[id][event.target.dataset.field]=event.target.value}save();progress()});document.addEventListener('change',event=>{const id=event.target.dataset.id;if(id){state[id]=state[id]||{};state[id][event.target.dataset.field]=event.target.value}save();progress()});function nextIncomplete(){const row=rows.find(item=>!complete(item.candidate_id));if(!row){alert('Tous les sites sont complets.');return}document.getElementById(`card-${row.candidate_id}`).scrollIntoView({behavior:'smooth',block:'start'})}function csvCell(v){v=String(v??'');return /[,"\r\n]/.test(v)?'"'+v.replaceAll('"','""')+'"':v}
function exportCsv(){save();if(!globalState.reviewer){alert('Renseigner le nom ou les initiales.');return}if(!globalState.review_date){alert('Renseigner la date de lecture.');return}const incomplete=rows.filter(row=>!complete(row.candidate_id)).length;if(incomplete&&!confirm(`${incomplete} site(s) incomplets. Exporter une sauvegarde provisoire ?`))return;const lines=[fields.join(',')];rows.forEach(row=>{const answer=state[row.candidate_id]||{};const merged={...row,...answer,review_role:'junior',review_status:'independent_preliminary',reviewer:globalState.reviewer,review_date:globalState.review_date};lines.push(fields.map(field=>csvCell(merged[field]??'')).join(','))});const blob=new Blob([String.fromCharCode(0xfeff)+lines.join('\r\n')],{type:'text/csv;charset=utf-8'});const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download=`iter9_hard_positive_review_${globalState.review_date}.csv`;link.click();URL.revokeObjectURL(link.href)}function clearReview(){if(confirm('Effacer toute la saisie enregistrée dans ce navigateur ?')){localStorage.removeItem(key);location.reload()}}
document.getElementById('reviewer').value=globalState.reviewer||'';document.getElementById('reviewDate').value=globalState.review_date||new Date().toISOString().slice(0,10);render();save();</script></body></html>'''
    (OUT / "review.html").write_text(
        template.replace("__ROWS__", payload).replace("__FIELDS__", fields),
        encoding="utf-8", newline="\n",
    )


def write_readme(rows: list[dict[str, str]]) -> None:
    slide_count = len({row["slide_id"] for row in rows})
    text = f"""# Revue des hard positives Iter9

Ce pack contient **{len(rows)} sites issus de {slide_count} WSI tumorales du jeu
d'entraînement**. Iter8 leur attribue une probabilité tumorale inférieure à
0,25 malgré leur position au cœur d'une annotation tumorale.

## Faire la revue

1. Ouvrir `review.html` dans Chrome, Edge, Firefox ou Safari.
2. Examiner le contexte, le zoom et le patch exact pour chaque site.
3. Renseigner les cinq champs obligatoires.
4. Cliquer sur **Exporter le CSV** après avoir renseigné le lecteur et la date.
5. Copier le CSV téléchargé dans ce dossier sans le modifier.

La saisie est sauvegardée automatiquement dans le navigateur. Le bouton
**Prochain incomplet** permet de reprendre la lecture. `review_template.csv`
offre une solution de secours pour une lecture dans un tableur.

## Règle d'inclusion dans Iter9

Un patch ne sera accepté que si toutes ces conditions sont réunies :

- `site_diagnosis = tumor` ;
- `image_quality` vaut `good` ou `interpretable_with_limitations` ;
- `confidence` vaut `medium` ou `high` ;
- `dominant_pattern` n'est pas `annotation_edge` ;
- `include_as_hard_positive = yes`.

Les réponses incertaines, de faible confiance ou non évaluables resteront dans
la trace de revue mais ne seront pas ajoutées au jeu d'entraînement.

## Garde-fou expérimental

La sélection utilise uniquement les 86 WSI tumorales du split d'entraînement.
Chaque lame fournit au maximum trois sites espacés d'au moins 1024 px, avec un
maximum global de 120. Aucune donnée de validation ou de test final n'est
utilisée. Iter9 ajoutera uniquement les hard positives confirmés à Iter8 ;
aucun nouveau hard négatif ne sera ajouté.
"""
    (OUT / "README_REVIEW.md").write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    rows = validate_and_prepare_rows()
    IMAGES.mkdir(parents=True, exist_ok=True)
    PATCHES.mkdir(parents=True, exist_ok=True)
    by_slide: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_slide.setdefault(row["slide_id"], []).append(row)
    completed = 0
    for slide_id, slide_rows in sorted(by_slide.items()):
        regions = parse_annotations(ANNOTATION_DIR / f"{slide_id}.xml")
        with openslide.OpenSlide(str(WSI_DIR / f"{slide_id}.tif")) as slide:
            for row in slide_rows:
                make_assets(slide, regions, row)
                completed += 1
                print(f"[{completed}/{len(rows)}] {row['candidate_id']}", flush=True)
    write_template(rows)
    write_html(rows)
    write_readme(rows)
    print(f"Review pack ready: {OUT}")


if __name__ == "__main__":
    main()
