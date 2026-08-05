from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlparse
import argparse
import csv
import html
import json
import shutil
import webbrowser


PACK_DIR = Path(__file__).resolve().parent

KEYS = {
    "h": ("other_hard_negative", "yes", "normal", "hard_negative", "Other hard negative"),
    "m": ("macrophage_histiocyte", "yes", "normal", "hard_negative", "Macrophage / histiocyte"),
    "s": ("sinus_histiocytosis", "yes", "normal", "hard_negative", "Sinus histiocytosis"),
    "f": ("fibrosis_stroma_benign", "yes", "normal", "hard_negative", "Benign fibrosis / stroma"),
    "g": ("electrocoagulation_artifact", "yes", "normal", "hard_negative", "Electrocoagulation artifact"),
    "c": ("crush_artifact_benign", "yes", "normal", "hard_negative", "Benign crush artifact"),
    "v": ("vessel_lumen", "yes", "normal", "hard_negative", "Vessel / lumen"),
    "o": ("outside_node_adipose", "yes", "normal", "hard_negative", "Outside node / adipose"),
    "n": ("necrosis_coagulation_benign", "yes", "normal", "hard_negative", "Benign necrosis / coagulation"),
    "a": ("generic_artifact", "yes", "normal", "hard_negative", "Generic artifact"),
    "b": ("benign_not_useful", "no", "normal", "easy_or_not_useful", "Benign but not useful"),
    "u": ("uncertain_review_later", "", "", "uncertain", "Uncertain / review later"),
    "x": ("reject_uninformative", "no", "", "reject", "Reject / uninformative"),
}

FIELD_EXTRAS = [
    "binary_label",
    "morphology_category",
    "difficulty_type",
    "review_category",
    "include_as_hard_negative",
    "reviewed_image",
    "sorted_path",
    "notes",
]


def read_rows(path):
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def write_rows(path, rows, fieldnames):
    for field in FIELD_EXTRAS:
        if field not in fieldnames:
            fieldnames.append(field)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def row_key(row):
    return tuple(str(row.get(key, "")).strip() for key in ["slide_id", "component_id", "candidate_id"])


def reviewed(row):
    return bool(row.get("review_category", "").strip()) or bool(row.get("include_as_hard_negative", "").strip())


def clean_rel_path(value):
    return str(value or "").replace("\\", "/")


def resolve_pack_path(value):
    rel = clean_rel_path(value)
    path = (PACK_DIR / rel).resolve()
    try:
        path.relative_to(PACK_DIR)
    except ValueError:
        return None
    if path.exists() and not path.name.startswith("._"):
        return path
    return None


def unique_destination(dst_dir, src_name):
    dst = dst_dir / src_name
    if not dst.exists():
        return dst
    src = Path(src_name)
    for idx in range(1, 10000):
        candidate = dst_dir / f"{src.stem}_{idx}{src.suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find destination for {dst}")


def copy_to_category(image_path, sorted_dir, category, row):
    category_dir = sorted_dir / category
    category_dir.mkdir(parents=True, exist_ok=True)
    parts = []
    for key in ["slide_id", "component_id", "candidate_id"]:
        if row.get(key):
            parts.append(f"{key}={row[key]}")
    prefix = "_".join(parts) or "row"
    dst = unique_destination(category_dir, f"{prefix}_{image_path.name}")
    shutil.copy2(image_path, dst)
    return dst


class ReviewState:
    def __init__(self, csv_path, reference_csv, sorted_dir, include_reviewed):
        self.csv_path = csv_path
        self.sorted_dir = sorted_dir
        self.include_reviewed = include_reviewed
        self.rows, self.fieldnames = read_rows(csv_path)
        ref_rows, _ = read_rows(reference_csv)
        self.references = {row_key(row): row for row in ref_rows}
        self.indices = list(range(len(self.rows))) if include_reviewed else [
            idx for idx, row in enumerate(self.rows) if not reviewed(row)
        ]
        self.cursor = 0

    def current_payload(self):
        total = len(self.rows)
        reviewed_count = sum(1 for row in self.rows if reviewed(row))
        if not self.indices or self.cursor >= len(self.indices):
            return {"done": True, "total": total, "reviewed": reviewed_count}

        row_idx = self.indices[self.cursor]
        row = self.rows[row_idx]
        ref = self.references.get(row_key(row), {})
        contact_sheet = clean_rel_path(row.get("contact_sheet", ""))
        overview = clean_rel_path(row.get("overview", ""))
        return {
            "done": False,
            "rowIndex": row_idx,
            "position": self.cursor + 1,
            "queueTotal": len(self.indices),
            "total": total,
            "reviewed": reviewed_count,
            "row": row,
            "reference": ref,
            "contactSheetUrl": f"/file?path={quote(contact_sheet)}" if contact_sheet else "",
            "overviewUrl": f"/file?path={quote(overview)}" if overview else "",
            "keys": {key: values[4] for key, values in KEYS.items()},
        }

    def advance(self):
        self.cursor += 1

    def back(self):
        self.cursor = max(0, self.cursor - 1)

    def save_key(self, key):
        if key not in KEYS or not self.indices or self.cursor >= len(self.indices):
            return
        row_idx = self.indices[self.cursor]
        row = self.rows[row_idx]
        category, include_value, binary_label, difficulty_type, _ = KEYS[key]
        image_path = resolve_pack_path(row.get("contact_sheet", ""))
        sorted_path = ""
        if image_path is not None:
            sorted_path = copy_to_category(image_path, self.sorted_dir, category, row)
            try:
                sorted_path = sorted_path.relative_to(PACK_DIR)
            except ValueError:
                pass
        row["binary_label"] = binary_label
        row["morphology_category"] = category
        row["difficulty_type"] = difficulty_type
        row["review_category"] = category
        row["include_as_hard_negative"] = include_value
        row["reviewed_image"] = clean_rel_path(row.get("contact_sheet", ""))
        row["sorted_path"] = str(sorted_path).replace("\\", "/")
        write_rows(self.csv_path, self.rows, self.fieldnames)
        self.advance()


def page_html():
    key_buttons = "".join(
        f"<button data-key='{html.escape(key)}'><b>{html.escape(key)}</b> {html.escape(label)}</button>"
        for key, (_, _, _, _, label) in KEYS.items()
    )
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>FP consensus review</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #101114; color: #f4f4f5; }}
    header {{ position: sticky; top: 0; z-index: 2; background: #181a1f; padding: 10px 14px; border-bottom: 1px solid #333842; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 10px 18px; font-size: 13px; color: #d7d7db; }}
    .ref {{ margin-top: 8px; padding: 8px 10px; background: #263247; border-left: 4px solid #7cb7ff; font-size: 14px; }}
    .current {{ margin-top: 6px; color: #ffd27d; font-size: 13px; }}
    main {{ display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 12px; padding: 12px; }}
    .viewer {{ background: #0b0c0f; border: 1px solid #2d3038; min-height: 70vh; display: grid; place-items: center; }}
    .viewer img {{ max-width: 100%; max-height: calc(100vh - 175px); object-fit: contain; }}
    aside {{ display: flex; flex-direction: column; gap: 8px; }}
    button {{ background: #242832; color: #f7f7f8; border: 1px solid #414754; padding: 8px 10px; text-align: left; border-radius: 6px; cursor: pointer; }}
    button:hover {{ background: #313747; }}
    .nav {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
    .small {{ font-size: 12px; color: #b9bbc4; line-height: 1.35; }}
    .done {{ padding: 40px; font-size: 20px; }}
  </style>
</head>
<body>
  <header>
    <div class="meta" id="meta"></div>
    <div class="ref" id="ref"></div>
    <div class="current" id="current"></div>
  </header>
  <main>
    <section class="viewer" id="viewer"></section>
    <aside>
      <div class="nav">
        <button data-action="back">← back</button>
        <button data-action="skip">skip →</button>
      </div>
      {key_buttons}
      <div class="small">Touches: h m s f g c v o n a b u x. Espace ou fleche droite = skip. Fleche gauche = back. Les reponses junior sont lues dans review_junior.csv; les decisions ici sont ecrites dans review_consensus.csv.</div>
    </aside>
  </main>
<script>
let state = null;

async function api(path, body) {{
  const options = body ? {{method: "POST", headers: {{"Content-Type": "application/json"}}, body: JSON.stringify(body)}} : {{}};
  const res = await fetch(path, options);
  return await res.json();
}}

function value(obj, key) {{
  return (obj && obj[key]) ? obj[key] : "—";
}}

function render(data) {{
  state = data;
  if (data.done) {{
    document.getElementById("viewer").innerHTML = `<div class="done">Termine. ${{data.reviewed}}/${{data.total}} lignes revues.</div>`;
    document.getElementById("meta").textContent = "";
    document.getElementById("ref").textContent = "";
    document.getElementById("current").textContent = "";
    return;
  }}
  const row = data.row;
  const ref = data.reference || {{}};
  document.getElementById("meta").innerHTML = [
    `ligne ${{data.rowIndex + 1}}/${{data.total}}`,
    `file ${{data.position}}/${{data.queueTotal}}`,
    `slide=${{value(row, "slide_id")}}`,
    `component=${{value(row, "component_id")}}`,
    `n=${{value(row, "n_patches")}}`,
    `max_prob=${{value(row, "max_prob")}}`
  ].map(x => `<span>${{x}}</span>`).join("");
  document.getElementById("ref").textContent =
    `REPONSE JUNIOR FIGEE: binaire=${{value(ref, "binary_label")}} | morphologie=${{value(ref, "morphology_category")}} | difficulte=${{value(ref, "difficulty_type")}} | inclusion=${{value(ref, "include_as_hard_negative")}} | notes=${{value(ref, "notes")}}`;
  document.getElementById("current").textContent =
    `Consensus actuel: ${{value(row, "review_category")}} / inclusion=${{value(row, "include_as_hard_negative")}}`;
  document.getElementById("viewer").innerHTML = `<img src="${{data.contactSheetUrl}}" alt="contact sheet">`;
}}

async function act(action, key=null) {{
  render(await api("/api/action", {{action, key}}));
}}

document.addEventListener("click", event => {{
  const button = event.target.closest("button");
  if (!button) return;
  if (button.dataset.key) act("save", button.dataset.key);
  if (button.dataset.action) act(button.dataset.action);
}});

document.addEventListener("keydown", event => {{
  if (!state || state.done) return;
  if (event.key === "ArrowRight" || event.key === " ") {{ event.preventDefault(); act("skip"); }}
  else if (event.key === "ArrowLeft" || event.key === "Backspace") {{ event.preventDefault(); act("back"); }}
  else if ("hmsfgcvonabux".includes(event.key)) {{ event.preventDefault(); act("save", event.key); }}
}});

api("/api/current").then(render);
</script>
</body>
</html>
"""


def json_response(handler, payload):
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/":
                data = page_html().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if parsed.path == "/api/current":
                json_response(self, state.current_payload())
                return
            if parsed.path == "/file":
                query = parse_qs(parsed.query)
                path = resolve_pack_path(unquote(query.get("path", [""])[0]))
                if path is None:
                    self.send_error(404)
                    return
                data = path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            self.send_error(404)

        def do_POST(self):
            if urlparse(self.path).path != "/api/action":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            action = payload.get("action")
            if action == "save":
                state.save_key(payload.get("key"))
            elif action == "skip":
                state.advance()
            elif action == "back":
                state.back()
            json_response(self, state.current_payload())

        def log_message(self, *_):
            return

    return Handler


def parse_args():
    parser = argparse.ArgumentParser(description="Browser-based FP consensus review.")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--reference-csv", required=True)
    parser.add_argument("--sorted-dir", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--include-reviewed", action="store_true")
    parser.add_argument("--open-browser", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    state = ReviewState(
        PACK_DIR / args.csv,
        PACK_DIR / args.reference_csv,
        PACK_DIR / args.sorted_dir,
        args.include_reviewed,
    )
    server = ThreadingHTTPServer((args.host, args.port), make_handler(state))
    url = f"http://{args.host}:{args.port}/"
    print("Review web app:", url)
    print("CSV consensus:", PACK_DIR / args.csv)
    print("Reference junior:", PACK_DIR / args.reference_csv)
    print("Ctrl+C pour arreter le serveur.")
    if args.open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServeur arrete.")


if __name__ == "__main__":
    main()
