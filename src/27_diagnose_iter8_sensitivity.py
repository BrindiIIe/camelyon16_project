from pathlib import Path
import csv, importlib.util
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('cc',ROOT/'src/10_eval_wsi_connected_components.py')
cc=importlib.util.module_from_spec(spec);spec.loader.exec_module(cc)
OUT=ROOT/'outputs/iter8_sensitivity_diagnostic';OUT.mkdir(exist_ok=True)
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(name,rows):cc.write_csv(OUT/name,rows,list(rows[0]))
def main():
    base=read(ROOT/'outputs/wsi_connected_components_iter8_val/per_slide_components.csv')
    old={r['slide_id']:r for r in read(ROOT/'outputs/wsi_connected_components_iter7_val_grid/per_slide_components.csv') if float(r['patch_threshold'])==.5 and int(r['min_component_size'])==40}
    comparison=[]
    for r in base:
        if r['true_label']=='1':
            o=old[r['slide_id']]
            comparison.append(dict(slide_id=r['slide_id'],iter7_prediction=o['pred_label'],iter8_prediction=r['pred_label'],iter7_largest=int(o['largest_component']),iter8_largest=int(r['largest_component']),iter7_positive_patches=o['positive_patches'],iter8_positive_patches=r['positive_patches'],iter7_max_prob=o['max_prob'],iter8_max_prob=r['max_prob']))
    write('tumor_comparison.csv',comparison)
    thresholds=[.01,.02,.05,.1,.15,.2,.25,.3,.4,.5]
    sizes=[1,2,3,5,10,15,20,30,40]
    per=[]
    for r in base:
        slide=r['slide_id']; data=cc.read_probs(ROOT/f'data/inference_iter8_val/{slide}_probs.csv')
        assert data,slide
        for t in thresholds:
            m=cc.evaluate_slide(data,t,1,128)
            per.append(dict(slide_id=slide,true_label=int(r['true_label']),patch_threshold=t,**m))
        print('Completed',slide,flush=True)
    write('per_slide_thresholds.csv',per)
    summaries=[]
    for t in thresholds:
        subset=[r for r in per if r['patch_threshold']==t]
        for size in sizes:
            predictions=[dict(r,pred_label=int(r['largest_component']>=size)) for r in subset]
            summaries.append(dict(patch_threshold=t,min_component_size=size,n_slides=len(subset),**cc.compute_summary(predictions)))
    write('summary_grid.csv',summaries)
    cc.write_markdown_table(OUT/'grid.md',summaries)
    lines=['# Iter8 sensitivity diagnostic','','Exploratory validation only: 48 slides, no retraining or final-test access.','No lesion localization is established by slide-level positivity.','','## Iter8 false negatives at 0.5/40','','| Slide | Iter7 largest component | Iter8 largest component | Iter7 positive |','| --- | ---: | ---: | ---: |']
    for r in comparison:
        if r['iter8_prediction']=='0':lines.append(f"| {r['slide_id']} | {r['iter7_largest']} | {r['iter8_largest']} | {r['iter7_prediction']} |")
    lines+=['','## Best specificity at sensitivity targets','']
    for target in [.8,.9,.95,1.0]:
        eligible=[r for r in summaries if r['sensitivity']>=target]
        if not eligible:lines.append(f'- Sensitivity >= {target:.0%}: no setting.');continue
        best=max(eligible,key=lambda r:(r['specificity'],r['sensitivity'],r['min_component_size'],r['patch_threshold']))
        lines.append(f"- Sensitivity >= {target:.0%}: threshold {best['patch_threshold']}, component {best['min_component_size']}; sensitivity {best['sensitivity']:.1%}, specificity {best['specificity']:.1%}, FN {best['fn']}, FP {best['fp']}.")
    (OUT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines),flush=True)
if __name__=='__main__':main()
