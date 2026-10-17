"""Build the independent junior review interface for the 36 Iter8 sites.

The script only reads metadata already present in the portable review pack.
It does not access WSI files and never copies validation images to training.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "portable_review_packs" / "iter8_targeted_histology_review"
SOURCE_CSV = PACK / "review_template.csv"
OUTPUT_CSV = PACK / "review_junior_template.csv"
OUTPUT_HTML = PACK / "review_junior.html"

METADATA_FIELDS = [
    "candidate_id",
    "slide_id",
    "x",
    "y",
    "selection_reason",
    "iter7_prob",
    "iter8_prob",
    "probability_drop",
    "image",
]

REVIEW_FIELDS = [
    "review_role",
    "review_status",
    "site_diagnosis",
    "dominant_pattern",
    "image_quality",
    "confidence",
    "likely_failure_mechanism",
    "reviewer",
    "review_date",
    "notes",
]


def read_rows() -> list[dict[str, str]]:
    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        source = list(csv.DictReader(stream))
    rows = []
    for source_row in source:
        row = {field: source_row.get(field, "") for field in METADATA_FIELDS}
        row.update(
            {
                "review_role": "junior",
                "review_status": "independent_preliminary",
                "site_diagnosis": "",
                "dominant_pattern": "",
                "image_quality": "",
                "confidence": "",
                "likely_failure_mechanism": "",
                "reviewer": "",
                "review_date": "",
                "notes": "",
            }
        )
        rows.append(row)
    if len(rows) != 36:
        raise ValueError(f"Expected 36 review sites, found {len(rows)}")
    return rows


def write_csv(rows: list[dict[str, str]]) -> None:
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=METADATA_FIELDS + REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def build_html(rows: list[dict[str, str]]) -> None:
    payload = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    output_fields = json.dumps(METADATA_FIELDS + REVIEW_FIELDS, ensure_ascii=False)
    overview_html = "".join(
        f'<details><summary>Vue d’ensemble {slide}</summary>'
        f'<img class="overview" src="overviews/{slide}.jpg" alt="Vue d’ensemble {slide}"></details>'
        for slide in ("tumor_071", "tumor_074", "tumor_096")
    )
    html = r'''<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lecture junior indépendante — revue histologique Iter8</title>
<style>
:root{--navy:#17324d;--blue:#24577f;--pale:#eef5fa;--green:#18794e;--amber:#9a6700;--red:#b42318;--border:#c8d2dc}
*{box-sizing:border-box}body{font-family:system-ui,-apple-system,sans-serif;margin:0;background:#f3f5f7;color:#17212b}
header{position:sticky;top:0;z-index:5;background:var(--navy);color:#fff;padding:12px 20px;box-shadow:0 2px 9px #0005}
.headrow{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.title{font-weight:750;font-size:1.05rem;margin-right:auto}
button,.button{border:1px solid #ffffff55;background:#fff;color:var(--navy);border-radius:5px;padding:8px 12px;font-weight:700;cursor:pointer}
button.secondary{background:transparent;color:#fff}.global{display:grid;grid-template-columns:minmax(210px,1fr) 170px;gap:10px;margin-top:10px;max-width:620px}
header label{font-size:.78rem;font-weight:700}header input{display:block;width:100%;margin-top:3px;padding:7px;border-radius:4px;border:0}
main{max-width:1500px;margin:auto;padding:18px}.warning{background:#fff4ce;border-left:5px solid #f0ad00;padding:12px 14px}.info{background:var(--pale);border-left:5px solid var(--blue);padding:12px 14px}
details{background:#fff;border:1px solid var(--border);border-radius:6px;margin:10px 0;padding:8px}summary{cursor:pointer;font-weight:700}.overview{display:block;max-width:100%;max-height:85vh;margin:10px auto 0}
.card{background:#fff;margin:22px 0;padding:16px;border-radius:8px;box-shadow:0 2px 8px #0002;border-left:6px solid #aab5bf;scroll-margin-top:145px}.card.complete{border-left-color:var(--green)}
.card h2{margin:0 0 5px}.status{font-size:.85rem;font-weight:750;color:#5f6b76}.complete .status{color:var(--green)}
.sheet{display:block;width:100%;max-height:82vh;object-fit:contain;background:#eee;margin-top:10px}.fields{display:grid;grid-template-columns:repeat(3,minmax(210px,1fr));gap:12px;margin-top:14px}
.fields label{font-size:.88rem;font-weight:700}.required::after{content:' *';color:var(--red)}select,textarea{display:block;width:100%;margin-top:4px;padding:8px;border:1px solid #aab5bf;border-radius:4px;background:#fff}textarea{min-height:82px;resize:vertical}
.model-info{font-family:ui-monospace,monospace;font-size:.86rem;color:#344}.footer-note{font-size:.85rem;color:#53606b}.danger{border-color:#ffb4ab!important;color:var(--red)!important}
@media(max-width:900px){header{position:static}.global,.fields{grid-template-columns:1fr}.card{scroll-margin-top:10px}}
</style>
</head>
<body>
<header>
  <div class="headrow">
    <span class="title">Lecture junior indépendante — Iter8</span>
    <span id="progress">0/36 complets</span>
    <button onclick="goToNextIncomplete()">Prochain incomplet</button>
    <button onclick="exportCsv()">Exporter le CSV junior</button>
    <button class="secondary danger" onclick="clearReview()">Effacer la saisie</button>
  </div>
  <div class="global">
    <label>Nom ou initiales du lecteur<input id="reviewer" autocomplete="name" placeholder="obligatoire pour l’export"></label>
    <label>Date de lecture<input id="reviewDate" type="date"></label>
  </div>
</header>
<main>
  <p class="warning"><strong>Données de validation.</strong> Cette lecture sert à comprendre la perte de sensibilité d’Iter8. Aucun patch de ce pack ne doit être ajouté à l’entraînement.</p>
  <p class="info"><strong>Statut :</strong> lecture junior indépendante et préliminaire. Ne pas consulter une lecture senior avant d’avoir exporté et figé ce CSV. Les métadonnées techniques sont conservées pour assurer la traçabilité de la sélection.</p>
  <p>Pour qu’un site soit compté comme complet, renseigner le diagnostic du patch central, le motif dominant, la qualité de l’image et le niveau de confiance. Le mécanisme d’échec et le commentaire peuvent rester vides si aucune conclusion supplémentaire n’est possible. La saisie est enregistrée automatiquement dans ce navigateur.</p>
  <h2>Vues d’ensemble</h2>
  __OVERVIEWS__
  <div id="cards"></div>
  <p class="footer-note">L’export contient les métadonnées de sélection et les réponses junior. Le statut reste « independent_preliminary » jusqu’à une éventuelle lecture senior indépendante puis une adjudication.</p>
</main>
<script>
const rows=__ROWS__;
const outputFields=__FIELDS__;
const storageKey='iter8_targeted_histology_review_junior_v2';
const stored=JSON.parse(localStorage.getItem(storageKey)||'{}');
let state=stored.rows||{};
const globalState=stored.global||{};
const requiredFields=['site_diagnosis','dominant_pattern','image_quality','confidence'];
const choices={
  site_diagnosis:[
    ['','— choisir —'],['tumor','Tumeur présente'],['benign','Tissu bénin'],['uncertain','Incertain'],['non_evaluable','Non évaluable']
  ],
  dominant_pattern:[
    ['','— choisir —'],['cohesive_metastasis','Métastase cohésive'],['small_tumor_clusters','Petits amas tumoraux'],['isolated_tumor_cells','Cellules tumorales isolées'],['low_tumor_fraction','Faible proportion tumorale'],['tumor_in_fibrosis_or_desmoplasia','Tumeur dans fibrose/desmoplasie'],['tumor_in_necrosis','Tumeur dans nécrose'],['benign_lymphoid_tissue','Tissu lymphoïde bénin'],['sinus_histiocytosis','Histiocytose sinusale'],['vessel_or_lumen','Vaisseau ou lumière'],['adipose_or_capsule','Tissu adipeux ou capsule'],['processing_artifact','Artefact de préparation'],['annotation_edge','Bord d’annotation'],['other','Autre'],['none','Aucun motif dominant'],['uncertain','Incertain']
  ],
  image_quality:[
    ['','— choisir —'],['good','Bonne'],['interpretable_with_limitations','Interprétable avec limites'],['non_evaluable','Non évaluable']
  ],
  confidence:[
    ['','— choisir —'],['high','Élevée'],['medium','Moyenne'],['low','Faible']
  ],
  likely_failure_mechanism:[
    ['','— facultatif —'],['subtle_tumor_morphology','Morphologie tumorale discrète'],['low_tumor_fraction','Faible proportion tumorale'],['fibrosis_or_desmoplasia','Fibrose ou desmoplasie'],['necrosis','Nécrose'],['artifact','Artefact'],['stain_or_color_shift','Variation de coloration'],['annotation_or_sampling','Annotation ou échantillonnage'],['class_exposure_shift','Déséquilibre de l’entraînement'],['unclear','Mécanisme non déterminé'],['not_applicable','Non applicable']
  ]
};
function esc(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function selectField(field,id,label,required=false){
  const value=state[id]?.[field]||'';
  const options=choices[field].map(([code,text])=>`<option value="${esc(code)}" ${value===code?'selected':''}>${esc(text)}</option>`).join('');
  return `<label><span class="${required?'required':''}">${esc(label)}</span><select data-id="${esc(id)}" data-field="${field}">${options}</select></label>`;
}
function isComplete(id){return requiredFields.every(field=>Boolean(state[id]?.[field]))}
function renderCards(){
  const cards=document.getElementById('cards');
  cards.innerHTML='';
  rows.forEach((row,index)=>{
    const id=row.candidate_id;
    const notes=state[id]?.notes||'';
    const complete=isComplete(id);
    cards.insertAdjacentHTML('beforeend',`<article class="card ${complete?'complete':''}" id="card-${esc(id)}">
      <h2>${index+1}/36 — ${esc(id)}</h2>
      <div class="status">${complete?'Complet':'À compléter'}</div>
      <img class="sheet" loading="lazy" src="${esc(row.image)}" alt="${esc(id)}">
      <details><summary>Afficher les informations du modèle</summary><p class="model-info">${esc(row.slide_id)} · centre (${esc(row.x)}, ${esc(row.y)}) · sélection=${esc(row.selection_reason)} · Iter7=${Number(row.iter7_prob).toFixed(4)} · Iter8=${Number(row.iter8_prob).toFixed(4)} · chute=${Number(row.probability_drop).toFixed(4)}</p></details>
      <div class="fields">
        ${selectField('site_diagnosis',id,'Diagnostic du patch central',true)}
        ${selectField('dominant_pattern',id,'Motif histologique dominant',true)}
        ${selectField('image_quality',id,'Qualité de l’image',true)}
        ${selectField('confidence',id,'Niveau de confiance',true)}
        ${selectField('likely_failure_mechanism',id,'Mécanisme probable de la perte de signal')}
        <label>Commentaire<textarea data-id="${esc(id)}" data-field="notes" placeholder="éléments morphologiques, limites ou hésitation">${esc(notes)}</textarea></label>
      </div>
    </article>`);
  });
  updateProgress();
}
function saveState(){
  globalState.reviewer=document.getElementById('reviewer').value.trim();
  globalState.review_date=document.getElementById('reviewDate').value;
  localStorage.setItem(storageKey,JSON.stringify({rows:state,global:globalState}));
}
function updateProgress(){
  const count=rows.filter(row=>isComplete(row.candidate_id)).length;
  document.getElementById('progress').textContent=`${count}/${rows.length} complets`;
  document.querySelectorAll('.card').forEach(card=>{
    const id=card.id.replace('card-','');
    const complete=isComplete(id);
    card.classList.toggle('complete',complete);
    card.querySelector('.status').textContent=complete?'Complet':'À compléter';
  });
}
document.addEventListener('input',event=>{
  const id=event.target.dataset.id;
  if(id){state[id]=state[id]||{};state[id][event.target.dataset.field]=event.target.value;}
  saveState();updateProgress();
});
document.addEventListener('change',event=>{
  const id=event.target.dataset.id;
  if(id){state[id]=state[id]||{};state[id][event.target.dataset.field]=event.target.value;}
  saveState();updateProgress();
});
function goToNextIncomplete(){
  const row=rows.find(item=>!isComplete(item.candidate_id));
  if(!row){alert('Les 36 sites sont complets.');return;}
  document.getElementById(`card-${row.candidate_id}`).scrollIntoView({behavior:'smooth',block:'start'});
}
function csvCell(value){
  value=String(value??'');
  return /[,"\r\n]/.test(value)?'"'+value.replaceAll('"','""')+'"':value;
}
function exportCsv(){
  saveState();
  const reviewer=globalState.reviewer||'';
  const reviewDate=globalState.review_date||'';
  if(!reviewer){alert('Renseigner le nom ou les initiales du lecteur avant l’export.');document.getElementById('reviewer').focus();return;}
  if(!reviewDate){alert('Renseigner la date de lecture avant l’export.');document.getElementById('reviewDate').focus();return;}
  const incomplete=rows.filter(row=>!isComplete(row.candidate_id)).length;
  if(incomplete && !confirm(`${incomplete} site(s) sont incomplets. Exporter tout de même une sauvegarde provisoire ?`))return;
  const lines=[outputFields.join(',')];
  rows.forEach(row=>{
    const answer=state[row.candidate_id]||{};
    const merged={...row,...answer,review_role:'junior',review_status:'independent_preliminary',reviewer,review_date:reviewDate};
    lines.push(outputFields.map(field=>csvCell(merged[field]??'')).join(','));
  });
  const blob=new Blob([String.fromCharCode(0xfeff)+lines.join('\r\n')],{type:'text/csv;charset=utf-8'});
  const link=document.createElement('a');
  link.href=URL.createObjectURL(blob);
  link.download=`iter8_targeted_histology_review_junior_${reviewDate}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}
function clearReview(){
  if(confirm('Effacer définitivement toute la saisie junior enregistrée dans ce navigateur ?')){
    localStorage.removeItem(storageKey);location.reload();
  }
}
document.getElementById('reviewer').value=globalState.reviewer||'';
document.getElementById('reviewDate').value=globalState.review_date||new Date().toISOString().slice(0,10);
renderCards();saveState();
</script>
</body>
</html>'''
    html = html.replace("__ROWS__", payload)
    html = html.replace("__FIELDS__", output_fields)
    html = html.replace("__OVERVIEWS__", overview_html)
    OUTPUT_HTML.write_text(html, encoding="utf-8", newline="\n")


def main() -> None:
    rows = read_rows()
    write_csv(rows)
    build_html(rows)
    print(f"Created {OUTPUT_HTML}")
    print(f"Created {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
