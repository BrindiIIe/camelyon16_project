"""Exploratory center-in-annotation localization on existing validation inference."""
from pathlib import Path
import csv
import os
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.matplotlib_cache'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PolygonPath

OUT = ROOT / 'outputs/iter8_localization_diagnostic'
RULES = [(0.5, 40), (0.3, 10), (0.15, 2), (0.25, 1)]


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def polygons(path):
    result = {'Tumor': [], 'Exclusion': []}
    for annotation in ET.parse(path).iter('Annotation'):
        group = annotation.get('PartOfGroup')
        if group not in result:
            raise ValueError(f'Unknown annotation group: {group}')
        coords = sorted(annotation.findall('./Coordinates/Coordinate'),
                        key=lambda c: int(c.get('Order')))
        points = np.array([(float(c.get('X')), float(c.get('Y'))) for c in coords])
        if len(points) < 3:
            raise ValueError(f'Invalid polygon in {path}')
        result[group].append(points)
    if not result['Tumor']:
        raise ValueError(f'No tumor annotation in {path}')
    return result


def inside_annotations(xy, regions):
    masks = {}
    for group, shapes in regions.items():
        mask = np.zeros(len(xy), dtype=bool)
        for shape in shapes:
            # Bounding-box filtering avoids testing all WSI points on large polygons.
            candidate = np.flatnonzero(np.all((xy >= shape.min(axis=0)) &
                                              (xy <= shape.max(axis=0)), axis=1))
            mask[candidate] |= PolygonPath(shape).contains_points(xy[candidate])
        masks[group] = mask
    return masks['Tumor'] & ~masks['Exclusion']


def component_stats(xy, positive, inside, minimum):
    remaining = {tuple(p): bool(hit) for p, hit in zip(xy[positive], inside[positive])}
    largest = qualifying = localized = largest_localized = 0
    while remaining:
        start, hit = remaining.popitem()
        stack = [start]
        size, hits = 0, int(hit)
        while stack:
            x, y = stack.pop()
            size += 1
            for dx, dy in [(-128,-128),(0,-128),(128,-128),(-128,0),
                           (128,0),(-128,128),(0,128),(128,128)]:
                neighbor = (x + dx, y + dy)
                if neighbor in remaining:
                    hits += int(remaining.pop(neighbor))
                    stack.append(neighbor)
        largest = max(largest, size)
        if hits:
            largest_localized = max(largest_localized, size)
        if size >= minimum:
            qualifying += 1
            localized += int(hits > 0)
    return dict(largest_component=largest, qualifying_components=qualifying,
                qualifying_components_with_tumor_center=localized,
                largest_component_with_tumor_center=largest_localized)


def main():
    source = read_csv(ROOT / 'outputs/iter8_sensitivity_diagnostic/tumor_comparison.csv')
    inventory = {r['slide_id']: r for r in read_csv(ROOT / 'outputs/splits/wsi_split_v1.csv')}
    assert len(source) == 19
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    for row in source:
        slide = row['slide_id']
        assert inventory[slide]['split'] == 'val', slide
        regions = polygons(ROOT / f'data/annotations/{slide}.xml')
        previous_xy = None
        plot = row['iter8_prediction'] == '0'
        if plot:
            fig, axes = plt.subplots(1, 2, figsize=(12, 7), constrained_layout=True)
        for model_index, model in enumerate(['iter7', 'iter8']):
            data = read_csv(ROOT / f'data/inference_{model}_val/{slide}_probs.csv')
            xy = np.array([(int(r['x']), int(r['y'])) for r in data], dtype=np.int64)
            prob = np.array([float(r['prob_tumor']) for r in data])
            finite = np.isfinite(prob)
            assert ((prob[finite] >= 0) & (prob[finite] <= 1)).all()
            assert not np.isinf(prob).any()
            assert len(np.unique(xy, axis=0)) == len(xy), slide
            if previous_xy is not None:
                assert np.array_equal(xy, previous_xy), f'Grid mismatch: {slide}'
            previous_xy = xy
            inside = inside_annotations(xy, regions)
            for threshold, minimum in RULES:
                positive = prob >= threshold
                stats = component_stats(xy, positive, inside, minimum)
                if threshold == 0.5:
                    assert stats['largest_component'] == int(row[f'{model}_largest'])
                results.append(dict(slide_id=slide, model=model, patch_threshold=threshold,
                    min_component_size=minimum, sampled_centers=len(xy),
                    missing_probabilities=int((~finite).sum()),
                    missing_probabilities_in_tumor=int((~finite & inside).sum()),
                    centers_in_tumor=int(inside.sum()),
                    positive_centers_in_tumor=int((positive & inside).sum()),
                    positive_centers_outside_tumor=int((positive & ~inside).sum()),
                    max_prob_in_tumor=float(prob[inside & finite].max()) if (inside & finite).any() else '',
                    **stats))
            if plot:
                ax = axes[model_index]
                ax.scatter(xy[::20, 0], xy[::20, 1], s=0.3, c='#dddddd', rasterized=True)
                selected = prob >= 0.15
                points = ax.scatter(xy[selected, 0], xy[selected, 1], s=3,
                                    c=prob[selected], cmap='viridis', vmin=0, vmax=1)
                for group, shapes in regions.items():
                    for shape in shapes:
                        closed = np.vstack([shape, shape[0]])
                        ax.plot(closed[:, 0], closed[:, 1], color='red' if group == 'Tumor' else 'orange', lw=0.7)
                ax.invert_yaxis()
                ax.set_aspect('equal')
                ax.set_title(f'{model}: {slide}')
                ax.set_xlabel('x (level-0 pixels)')
                ax.set_ylabel('y (level-0 pixels)')
        if plot:
            fig.colorbar(points, ax=axes, label='Tumor probability (shown >= 0.15)', shrink=0.65)
            fig.suptitle('Red: XML tumor contour. Gray: sampled grid (1/20).\nCoordinate map; no histological image.')
            fig.savefig(OUT / f'{slide}_localization.png', dpi=150)
            plt.close(fig)
        print(f'Completed {slide}', flush=True)
    with (OUT / 'localization.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    lines = ['# Iter8: localisation exploratoire sur validation', '',
        '19 lames tumorales de validation; inférences existantes, aucune nouvelle inférence.',
        'Coordonnées CSV = centres des patches de 256 px, niveau 0; voisinage à 8, pas 128 px.',
        'Localisation = au moins un centre dans un polygone Tumor, hors Exclusion.',
        'Les probabilités NaN ne passent aucun seuil, comme dans les évaluations précédentes; leur nombre est conservé dans le CSV. Elles ne sont pas assimilables à des prédictions négatives valides.',
        'Une composante qualifiante peut contenir des centres hors tumeur. Ce diagnostic ne mesure ni une surface de recouvrement ni une sensibilité par lésion.',
        'Les points exactement sur les contours ont une appartenance numériquement ambiguë. Les tumeurs sans centre échantillonné ne sont pas évaluables par ce critère.',
        'Les cartes sont géométriques; une revue histologique reste nécessaire. Les règles alternatives sont sélectionnées sur validation.', '',
        '| Modèle | Règle | Lames positives /19 | Avec composante qualifiante localisée /19 |',
        '| --- | --- | ---: | ---: |']
    for model in ['iter7', 'iter8']:
        for threshold, minimum in RULES:
            subset = [r for r in results if r['model'] == model and r['patch_threshold'] == threshold]
            lines.append(f"| {model} | {threshold}/{minimum} | {sum(r['qualifying_components'] > 0 for r in subset)} | {sum(r['qualifying_components_with_tumor_center'] > 0 for r in subset)} |")
    lines += ['', '## Huit faux négatifs iter8 à la règle 0.5/40', '',
              '| Lame | Centres annotés échantillonnés | Centres positifs annotés iter7 → iter8 | Plus grande composante avec centre tumoral iter7 → iter8 |',
              '| --- | ---: | ---: | ---: |']
    for row in source:
        if row['iter8_prediction'] != '0':
            continue
        pair = [next(r for r in results if r['slide_id'] == row['slide_id'] and r['model'] == m and r['patch_threshold'] == 0.5) for m in ['iter7','iter8']]
        a, b = pair
        lines.append(f"| {row['slide_id']} | {a['centers_in_tumor']} | {a['positive_centers_in_tumor']} → {b['positive_centers_in_tumor']} | {a['largest_component_with_tumor_center']} → {b['largest_component_with_tumor_center']} |")
    lines += ['', '## Interprétation et suite', '',
        '- À 0.5/40, iter7 a 16 lames positives mais seulement 14 avec une composante qualifiante contenant un centre tumoral; iter8 en a 11 dans les deux cas.',
        '- Sur tumor_017 et tumor_081, les composantes qualifiantes iter7 ne contiennent aucun centre tumoral. Leur ancienne positivité ne prouvait donc pas une localisation tumorale selon ce critère.',
        '- La régression localisée à 0.5/40 concerne tumor_071, tumor_074 et tumor_096. Elle justifie une revue histologique ciblée et un examen de l’exposition aux patches tumoraux pendant l’entraînement.',
        '- Les règles alternatives iter8 retrouvent des composantes avec centre tumoral sur 16, 18 et 19 lames, mais leurs spécificités de validation sont respectivement 62.1%, 41.4% et 27.6% (diagnostic précédent).',
        '- Une seule probabilité NaN a été trouvée: iter7, tumor_014, hors annotation tumorale. Les grilles des deux modèles sont identiques sur les 19 lames; les composantes à 0.5 reproduisent les résultats antérieurs.',
        '- Avant un éventuel iter9: revue des images histologiques sur les trois régressions localisées; définir ensuite une expérience contrôlée sur train. Ne pas ajouter ces patches de validation au train.',
        '- Aucun entraînement lancé et aucun accès aux lames test_final.']
    (OUT / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
