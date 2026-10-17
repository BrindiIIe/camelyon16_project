# Iter8: localisation exploratoire sur validation

19 lames tumorales de validation; inférences existantes, aucune nouvelle inférence.
Coordonnées CSV = centres des patches de 256 px, niveau 0; voisinage à 8, pas 128 px.
Localisation = au moins un centre dans un polygone Tumor, hors Exclusion.
Les probabilités NaN ne passent aucun seuil, comme dans les évaluations précédentes; leur nombre est conservé dans le CSV. Elles ne sont pas assimilables à des prédictions négatives valides.
Une composante qualifiante peut contenir des centres hors tumeur. Ce diagnostic ne mesure ni une surface de recouvrement ni une sensibilité par lésion.
Les points exactement sur les contours ont une appartenance numériquement ambiguë. Les tumeurs sans centre échantillonné ne sont pas évaluables par ce critère.
Les cartes sont géométriques; une revue histologique reste nécessaire. Les règles alternatives sont sélectionnées sur validation.

| Modèle | Règle | Lames positives /19 | Avec composante qualifiante localisée /19 |
| --- | --- | ---: | ---: |
| iter7 | 0.5/40 | 16 | 14 |
| iter7 | 0.3/10 | 19 | 19 |
| iter7 | 0.15/2 | 19 | 19 |
| iter7 | 0.25/1 | 19 | 19 |
| iter8 | 0.5/40 | 11 | 11 |
| iter8 | 0.3/10 | 16 | 16 |
| iter8 | 0.15/2 | 18 | 18 |
| iter8 | 0.25/1 | 19 | 19 |

## Huit faux négatifs iter8 à la règle 0.5/40

| Lame | Centres annotés échantillonnés | Centres positifs annotés iter7 → iter8 | Plus grande composante avec centre tumoral iter7 → iter8 |
| --- | ---: | ---: | ---: |
| tumor_017 | 12 | 12 → 10 | 12 → 7 |
| tumor_040 | 31 | 27 → 24 | 34 → 20 |
| tumor_043 | 19 | 15 → 6 | 18 → 5 |
| tumor_067 | 8 | 6 → 8 | 11 → 12 |
| tumor_071 | 3315 | 1952 → 1 | 538 → 1 |
| tumor_074 | 506 | 499 → 171 | 792 → 30 |
| tumor_081 | 30 | 23 → 0 | 26 → 0 |
| tumor_096 | 1382 | 542 → 0 | 252 → 0 |

## Interprétation et suite

- À 0.5/40, iter7 a 16 lames positives mais seulement 14 avec une composante qualifiante contenant un centre tumoral; iter8 en a 11 dans les deux cas.
- Sur tumor_017 et tumor_081, les composantes qualifiantes iter7 ne contiennent aucun centre tumoral. Leur ancienne positivité ne prouvait donc pas une localisation tumorale selon ce critère.
- La régression localisée à 0.5/40 concerne tumor_071, tumor_074 et tumor_096. Elle justifie une revue histologique ciblée et un examen de l’exposition aux patches tumoraux pendant l’entraînement.
- Les règles alternatives iter8 retrouvent des composantes avec centre tumoral sur 16, 18 et 19 lames, mais leurs spécificités de validation sont respectivement 62.1%, 41.4% et 27.6% (diagnostic précédent).
- Une seule probabilité NaN a été trouvée: iter7, tumor_014, hors annotation tumorale. Les grilles des deux modèles sont identiques sur les 19 lames; les composantes à 0.5 reproduisent les résultats antérieurs.
- Avant un éventuel iter9: revue des images histologiques sur les trois régressions localisées; définir ensuite une expérience contrôlée sur train. Ne pas ajouter ces patches de validation au train.
- Aucun entraînement lancé et aucun accès aux lames test_final.
