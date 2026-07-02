# Projet de thèse - Détection de métastases ganglionnaires par IA sur lames virtuelles

## 1. Question clinique

L'objectif du projet est de développer et d'évaluer un pipeline d'aide à la détection de métastases ganglionnaires sur lames histologiques numérisées, à partir du jeu de données public CAMELYON16.

La question principale est:

> Un pipeline d'apprentissage profond peut-il identifier des zones suspectes de métastase sur des lames ganglionnaires entières, avec une sortie interprétable sous forme de heatmap et une décision au niveau lame ?

L'enjeu clinique est double:

- réduire le risque de méconnaître une zone tumorale, notamment de petite taille;
- limiter les faux positifs isolés, qui peuvent rendre l'outil inutilisable en pratique.

## 2. Pipeline actuel

Un prototype fonctionnel est déjà en place.

Le pipeline actuel comprend:

1. Extraction de patches à partir de lames WSI CAMELYON16.
2. Utilisation des annotations XML pour distinguer patches tumoraux et normaux.
3. Entraînement d'un classifieur patch-level basé sur ResNet18.
4. Inférence sur lame entière par balayage de la zone tissulaire.
5. Génération de heatmaps de probabilité tumorale.
6. Décision au niveau WSI par composantes connexes de patches positifs.
7. Analyse séparée des petits clusters très suspects, afin de ne pas ignorer les micro-métastases potentielles.

Le modèle actuellement le plus pertinent est l'itération `iter2`, issue d'un enrichissement progressif du jeu d'entraînement par erreurs difficiles.

## 3. Résultats préliminaires

### Évaluation patch-level

Quatre jeux d'entraînement ont été comparés: baseline, iter1, iter2, iter3.

Le meilleur compromis actuel est `iter2`.

| Expérience | Seuil | Précision tumorale val | Rappel tumoral val | F1 val | Précision tumorale test | Rappel tumoral test | F1 test |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0.2 | 0.686 | 0.828 | 0.750 | 0.833 | 1.000 | 0.909 |
| iter1 | 0.3 | 0.966 | 0.966 | 0.966 | 0.909 | 1.000 | 0.952 |
| iter2 | 0.5 | 0.967 | 1.000 | 0.983 | 0.909 | 1.000 | 0.952 |
| iter3 | 0.5 | 0.966 | 0.966 | 0.966 | 1.000 | 0.700 | 0.824 |

Ces résultats sont encourageants, mais restent insuffisants seuls car l'évaluation patch-level ne reflète pas directement l'usage clinique sur lame entière.

### Évaluation WSI-level

Le modèle `iter2` a été appliqué à 20 lames entières:

- 10 lames tumorales;
- 10 lames normales.

Une règle simple basée sur une composante connexe de patches positifs a été testée.

Exemple de réglage performant:

```text
patch_threshold = 0.5
minimum connected component size = 40 patches
```

Sur ces 20 lames, ce réglage obtient:

```text
sensibilité = 1.000
spécificité = 1.000
TP = 10, FP = 0, FN = 0, TN = 10
```

Ce résultat doit être interprété prudemment, car il est obtenu sur un faible nombre de lames et nécessite une validation sur un vrai split WSI validation/test.

## 4. Point méthodologique important

Un critère fondé uniquement sur une grande composante connexe est spécifique, mais risque de manquer de très petites métastases.

Pour cette raison, une stratégie complémentaire a été développée:

- **mode spécifique**: grande composante de probabilité modérée;
- **mode sensible**: petit cluster de très haute probabilité;
- **mode hybride**: combinaison des deux.

Les premiers résultats montrent que les micro-clusters sont sensibles mais génèrent des faux positifs sur certaines lames normales. Ils semblent donc utiles comme outil de revue ciblée, mais pas encore comme décision automatique finale.

## 5. Ce que le projet nécessite maintenant

Le pipeline technique existe, mais il a besoin d'un encadrement médical/anatomopathologique pour devenir un travail de thèse robuste.

L'apport attendu d'un encadrant médecin ou pathologiste serait:

- valider la pertinence clinique de la question;
- aider à définir une stratégie d'évaluation réaliste;
- relire les heatmaps et les faux positifs;
- distinguer les faux positifs techniques des zones histologiquement ambiguës;
- décider comment traiter les micro-clusters suspects;
- aider à formuler les limites du travail;
- orienter la présentation des résultats pour une thèse ou un article.

L'encadrant n'a pas besoin d'être spécialiste en IA. L'expertise indispensable est surtout anatomopathologique et clinique.

## 6. Perspectives de publication

Le projet pourrait devenir publiable s'il est consolidé méthodologiquement.

Les axes valorisables sont:

- mise en place d'un pipeline reproductible de détection sur WSI;
- comparaison patch-level versus WSI-level;
- analyse de l'effet des composantes connexes sur la réduction des faux positifs;
- étude spécifique des petits clusters suspects et du risque de micro-métastases;
- validation qualitative des heatmaps par un pathologiste;
- éventuelle comparaison entre stratégie sensible et stratégie spécifique.

Une publication ne reposerait pas seulement sur le fait d'avoir entraîné un réseau de neurones, mais sur l'analyse clinique et méthodologique du passage d'un modèle patch-level à une décision interprétable au niveau lame.

## 7. Prochaines étapes proposées

1. Revue des heatmaps générées sur les 20 WSI.
2. Identification des faux positifs sur lames normales.
3. Analyse des micro-clusters très suspects.
4. Validation ou rejet de ces zones par lecture anatomopathologique.
5. Extraction de nouveaux hard negatives si nécessaire.
6. Entraînement d'une nouvelle itération du modèle.
7. Constitution d'un vrai split WSI validation/test.
8. Rédaction d'une section Méthodes et Résultats préliminaires.

## 8. Message court de présentation

> J'ai développé un prototype fonctionnel de pipeline de détection de métastases ganglionnaires sur lames virtuelles CAMELYON16. Le pipeline entraîne un modèle patch-level, réalise une inférence sur lame entière, génère des heatmaps et propose une décision WSI-level par composantes connexes. Les premiers résultats sont encourageants, mais le projet nécessite maintenant une validation anatomopathologique des heatmaps, des faux positifs et des petits clusters suspects afin d'en faire un travail de thèse robuste et potentiellement publiable.
