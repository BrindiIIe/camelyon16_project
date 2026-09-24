from pathlib import Path
import csv
import json
import subprocess
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / 'outputs/inference_queues/iter8_val_queue.csv'
STATUS = ROOT / 'outputs/iter8_wsi_validation_status.json'

def read(path):
    with path.open(newline='', encoding='utf-8-sig') as handle:
        return list(csv.DictReader(handle))

def status(state, **extra):
    STATUS.write_text(json.dumps(dict(state=state, updated_at=datetime.now().isoformat(), **extra), indent=2), encoding='utf-8')

def run(script, *args):
    subprocess.run([sys.executable, '-u', str(ROOT / 'src' / script), *args], cwd=ROOT, check=True)

def main():
    rows = read(QUEUE)
    expected = {r['slide_id'] for r in read(ROOT / 'outputs/splits/wsi_split_v1.csv') if r['split'] == 'val'}
    assert len(rows) == 48 and {r['slide_id'] for r in rows} == expected
    assert all(r['split'] == 'val' for r in rows)
    status('inference_running')
    run('21_run_inference_queue.py', '--queue-csv', str(QUEUE), '--model-path', 'models/best_resnet18_patch_iter8.pt', '--output-dir', 'data/inference_iter8_val', '--device', 'cpu', '--stride', '128', '--batch-size', '128', '--progress-every', '10', '--resume')
    assert all(r['status'] == 'done' for r in read(QUEUE))
    assert all((ROOT / 'data/inference_iter8_val' / f'{s}_probs.csv').is_file() for s in expected)
    status('evaluation_running')
    common = ['--csv-dir', 'data/inference_iter8_val', '--slides', *sorted(expected), '--stride', '128']
    run('10_eval_wsi_connected_components.py', *common, '--output-dir', 'outputs/wsi_connected_components_iter8_val', '--patch-thresholds', '0.5', '--min-component-sizes', '40')
    grid = read(ROOT / 'outputs/wsi_connected_components_iter7_val_grid/summary_components.csv')
    thresholds = sorted({r['patch_threshold'] for r in grid}, key=float)
    sizes = sorted({r['min_component_size'] for r in grid}, key=int)
    run('10_eval_wsi_connected_components.py', *common, '--output-dir', 'outputs/wsi_connected_components_iter8_val_grid', '--patch-thresholds', *thresholds, '--min-component-sizes', *sizes)
    result = read(ROOT / 'outputs/wsi_connected_components_iter8_val/summary_components.csv')[0]
    assert int(result['n_slides']) == 48
    previous = next(r for r in grid if float(r['patch_threshold']) == .5 and int(r['min_component_size']) == 40)
    metrics = ['sensitivity', 'specificity', 'precision', 'f1', 'accuracy', 'tp', 'fp', 'fn', 'tn']
    lines = ['# Iter8 WSI validation', '', 'Completed on all 48 validation WSI (29 normal, 19 tumor), corrected tissue mask, stride 128. Final test untouched.', '', 'Frozen rule: probability >= 0.5, component size >= 40.', '', '| Model | ' + ' | '.join(metrics) + ' |', '| --- | ' + ' | '.join(['---:'] * len(metrics)) + ' |']
    for name, row in [('iter7', previous), ('iter8', result)]:
        lines.append('| ' + name + ' | ' + ' | '.join(row[m] for m in metrics) + ' |')
    lines += ['', 'Validation-only grid: outputs/wsi_connected_components_iter8_val_grid/.', 'Grid settings match iter7; this is validation performance, not final-test performance.']
    (ROOT / 'outputs/iter8_wsi_validation_summary.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    status('complete', frozen_rule_metrics=result)
    print('Iter8 WSI validation complete.', flush=True)

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        status('failed', error=repr(exc))
        raise
