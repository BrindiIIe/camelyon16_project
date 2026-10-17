# Gel du comparateur supervisé

## Décision

Le comparateur supervisé est figé avant toute inférence sur le jeu
`test_final`.

- modèle : `iter8` ;
- checkpoint : `models/best_resnet18_patch_iter8.pt` ;
- empreinte SHA-256 : `00c243996e6ea1ae402a4be709624f2d1a7a4d4e3f7d0d9a9c675f517b7b2eed` ;
- seuil patch : 0.25 ;
- taille minimale de composante : 1 patch ;
- stride : 128 pixels.

## Critère défini avant le test final

La règle maximise la spécificité parmi les couples modèle/règle détectant les
19 lames tumorales de validation, soit une sensibilité de 100 %. En cas
d'égalité de performance, la règle la plus proche du point de référence
historique 0,5/40 est retenue.

## Performance de validation du choix figé

| Sensibilité | Spécificité | Précision | F1 | Exactitude | VP | FP | FN | VN |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.000 | 0.276 | 0.475 | 0.644 | 0.562 | 19 | 21 | 0 | 8 |

La grille commune comprend 14 seuils et
17 tailles de composante pour `iter7` et `iter8`. Les 125
lames de `test_final` n'ont pas été lues pour prendre cette décision. Le
fichier `freeze_decision.json` constitue la spécification exécutable de
l'évaluation finale.
