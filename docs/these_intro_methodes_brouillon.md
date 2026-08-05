# Brouillon introduction et méthodes

## Titre de travail

Développement et évaluation d'un pipeline d'intelligence artificielle pour la
détection de métastases ganglionnaires mammaires sur lames histologiques
numérisées.

## Fil conducteur

Ce travail s'inscrit dans la transition numérique récente du service
d'anatomie et cytologie pathologiques, dont les lames sont numérisées depuis
environ deux ans. L'objectif final est d'évaluer, sur des lames issues du
service, la performance de modèles d'intelligence artificielle pour la
détection de métastases ganglionnaires mammaires, et de comparer un modèle
supervisé entraîné localement à des modèles fondationnels récents tels qu'UNI
et Virchow.

La première étape, présentée ici, consiste à construire et valider
méthodologiquement la chaîne complète sur le jeu public CAMELYON16 : extraction
de patches, apprentissage supervisé, inférence sur lame entière, génération de
cartes de chaleur, décision au niveau de la lame et analyse des faux positifs.

## Introduction

### Cancer du sein et enjeu ganglionnaire

Le cancer du sein est le cancer le plus fréquent chez la femme dans le monde.
Selon les estimations GLOBOCAN 2022 relayées par l'Organisation mondiale de la
santé, environ 2,3 millions de nouveaux cas et 670 000 décès par cancer du sein
ont été recensés dans le monde en 2022 [@whoBreastCancer2026;
@globocanBreastCancer2022]. En France, il constitue également le cancer le plus
fréquent chez la femme, avec 61 214 nouveaux cas estimés en France
métropolitaine en 2023 et 12 757 décès en 2022 selon l'Institut national du
cancer [@incaCancerSein2026]. Santé publique France souligne une augmentation
de l'incidence sur les dernières décennies, contrastant avec une diminution de
la mortalité, dans un contexte de dépistage, d'amélioration des traitements et
de prise en charge plus précoce [@spfCancerSein2025].

Le statut ganglionnaire reste un élément majeur de la stadification et de la
prise en charge des cancers du sein. La présence de métastases dans les
ganglions lymphatiques influence le pronostic, l'indication de traitements
adjuvants et l'évaluation du risque de récidive. Son analyse repose sur
l'examen anatomopathologique de lames histologiques, tâche qui peut être longue
et répétitive lorsque de nombreux ganglions doivent être examinés, avec un
enjeu particulier pour les petites lésions, notamment les micrométastases et
les cellules tumorales isolées.

### Numérisation de l'anatomopathologie

La pathologie numérique repose sur la numérisation des lames histologiques en
images de lame entière, ou whole-slide images (WSI). Cette transformation
modifie progressivement les pratiques : lecture à distance, partage d'expertise,
archivage numérique, enseignement, recherche et développement d'outils d'aide
au diagnostic. En France, cette transition reste hétérogène mais s'accélère,
notamment sous l'impulsion de projets institutionnels et du rapport
ministériel consacré à la politique de numérisation de l'anatomie et cytologie
pathologiques [@rapportNumerisationACP2025]. Ce rapport insiste sur les enjeux
d'infrastructure, d'interopérabilité, d'organisation territoriale, de stockage,
de souveraineté des données et de préparation à l'arrivée de l'intelligence
artificielle.

Dans le service où s'inscrit ce travail, la numérisation des lames a été mise
en place il y a environ deux ans. Ce contexte local crée une opportunité
méthodologique : les lames numériques peuvent être réutilisées pour développer
des pipelines reproductibles d'analyse d'image, évaluer des algorithmes dans
des conditions proches de la pratique réelle, et préparer l'intégration
raisonnée d'outils d'aide au diagnostic.

### Intelligence artificielle en pathologie mammaire

L'intelligence artificielle appliquée aux WSI a montré des résultats
prometteurs dans plusieurs tâches de pathologie mammaire : détection de zones
tumorales, évaluation de biomarqueurs, quantification de l'expression HER2,
grading, détection de mitoses et identification de métastases ganglionnaires
[@solimanBreastAI2024; @katayamaBreastPathologyAI2024]. Le challenge
CAMELYON16 a constitué une étape importante pour l'évaluation de systèmes de
deep learning capables de détecter les métastases ganglionnaires mammaires sur
lames entières [@ehteshamiBejnordiCamelyon2017]. Cette étude a montré que des
algorithmes pouvaient atteindre des performances élevées, parfois comparables à
celles de pathologistes dans certaines conditions expérimentales.

Cependant, le passage d'une performance algorithmique à une utilisation
clinique fiable reste complexe. Les WSI sont des images gigapixels, issues de
processus techniques variables : fixation, inclusion, coloration, scanner,
résolution, compression et artefacts. Les modèles peuvent être sensibles à ces
variations et produire des faux positifs sur des structures bénignes ou
artefactuelles. La validation externe, la robustesse inter-centres, la
gestion des petites lésions et l'intégration dans un workflow médical restent
des limites majeures de la littérature [@aiLymphNodeMetastasesReview2023;
@digitalPathologyRoutineReview2024].

### Modèles fondationnels en pathologie numérique

Plus récemment, les modèles fondationnels ont modifié le paysage de la
pathologie computationnelle. Ces modèles sont pré-entraînés de manière
auto-supervisée sur de très grands volumes d'images histologiques, puis
réutilisés comme extracteurs de caractéristiques pour des tâches spécifiques.
UNI, publié dans Nature Medicine en 2024, est un encodeur visuel généraliste
pour la pathologie anatomique, pré-entraîné sur un très grand corpus
multi-organes et évalué sur de nombreuses tâches cliniques
[@chenUNI2024]. Virchow, également publié en 2024, a été entraîné sur environ
1,5 million de WSI H&E issues de données cliniques, avec l'objectif de servir
de base à des modèles de pathologie computationnelle à grande échelle
[@vorontsovVirchow2024].

Ces modèles ouvrent des perspectives importantes, mais leur intérêt réel doit
être évalué dans des contextes précis : tâche clinique définie, données locales,
contraintes de calcul, interprétabilité, intégration dans le laboratoire et
comparaison avec des approches supervisées plus simples. Dans ce contexte, la
construction d'un pipeline local contrôlé sur CAMELYON16 représente une étape
préparatoire nécessaire avant l'évaluation sur les lames du service et la
comparaison avec UNI et Virchow.

### Objectifs

L'objectif principal de ce travail préliminaire est de développer un pipeline
interprétable de détection de métastases ganglionnaires mammaires sur lames
entières, à partir du jeu public CAMELYON16.

Les objectifs secondaires sont :

- entraîner et comparer plusieurs itérations d'un classifieur patch-level ;
- générer des heatmaps tumorales sur WSI ;
- transformer les probabilités patch-level en décision au niveau de la lame à
  l'aide de composantes connexes ;
- analyser les faux positifs et faux négatifs afin de guider un hard-mining
  contrôlé ;
- préparer l'évaluation ultérieure sur des lames du service ;
- poser le cadre méthodologique d'une comparaison future avec des modèles
  fondationnels tels qu'UNI et Virchow.

## Méthodes

### Type d'étude

Il s'agit d'une étude méthodologique rétrospective portant sur des lames
histologiques numérisées. La phase actuelle utilise le jeu de données public CAMELYON16
comme base de développement. Ce choix permet de disposer de WSI annotées,
d'annotations tumorales XML et d'un cadre de comparaison connu dans la
littérature. L'étude vise à construire une chaîne complète allant de la lame
entière à une décision interprétable au niveau WSI.

### Données

Les données utilisées proviennent du challenge CAMELYON16, consacré à la
détection de métastases de cancer du sein dans les ganglions lymphatiques. Les
WSI sont des lames H&E numérisées. Les lames tumorales disposent d'annotations
délimitant les régions métastatiques.

Dans l'état actuel du projet, l'inventaire local comprend :

- 155 WSI normales ;
- 105 WSI tumorales ;
- 125 WSI issues du groupe test ;
- des annotations XML associées aux lames tumorales disponibles.

Un split au niveau lame a été créé afin d'éviter les fuites d'information entre
entraînement, validation et test final. Les lames déjà utilisées pour
l'exploration, la revue visuelle ou le hard-mining ont été forcées dans le
split d'entraînement et exclues du test final.

Le split actuel est :

| Split | Normales | Tumorales | Total |
| --- | ---: | ---: | ---: |
| Entraînement | 126 | 86 | 212 |
| Validation | 29 | 19 | 48 |
| Test final | 79 | 46 | 125 |

Pour les lames `test_*`, le statut tumoral est actuellement inféré à partir de
la présence d'un fichier XML : XML présent pour les lames considérées comme
tumorales, absence d'XML pour les lames considérées comme normales. Cette
convention devra être vérifiée avec les métadonnées officielles CAMELYON16
avant toute présentation définitive des résultats sur test final.

### Prétraitement et extraction de patches

Les WSI sont analysées à partir d'un masque tissulaire permettant d'éviter le
balayage des zones de fond. Des patches RGB de taille fixe sont extraits sur la
zone tissulaire. Les annotations XML des lames tumorales sont utilisées pour
attribuer un label tumoral ou normal aux patches selon leur position par
rapport aux régions annotées. Les patches extraits constituent les jeux
d'entraînement, de validation et de test patch-level.

Les scripts principaux utilisés pour cette étape sont :

- `src/tissue_utils.py` pour les fonctions d'extraction ;
- `src/02_split_dataset.py` pour la constitution du split patch-level initial ;
- `src/build_train_dataset.py` et les scripts de préparation itérative pour les
  enrichissements successifs.

### Modèle supervisé patch-level

Le modèle supervisé de base est un ResNet18 entraîné comme classifieur binaire
de patches : tissu normal versus tissu tumoral. Plusieurs itérations ont été
entraînées afin d'étudier l'effet de l'enrichissement progressif par cas
difficiles.

Les principales itérations sont :

- `baseline` : modèle initial ;
- `iter1`, `iter2`, `iter3` : enrichissements progressifs précoces ;
- `iter4` : ajout de micro faux positifs revus comme hard negatives ;
- `iter5` : ajout de faux positifs d'`iter4` et de hard positives ;
- `iter6` : retour à la base `iter2` avec ajout de 120 hard negatives issus
  de faux positifs WSI récemment revus.

Le modèle `iter2` constitue actuellement le modèle de référence, car il
présentait le meilleur compromis initial entre performance patch-level et
performance WSI-level. Le modèle `iter6` est une itération récente visant à
réduire les faux positifs WSI sans reprendre l'enrichissement hard-positive
important qui avait rendu `iter5` plus permissif.

### Inférence sur lame entière

L'inférence WSI repose sur un balayage de la zone tissulaire par patches. Pour
chaque position, le modèle estime une probabilité tumorale. Les résultats sont
stockés dans des fichiers CSV contenant les coordonnées `x`, `y` et la
probabilité tumorale.

Le script `src/05_infer_wsi.py` permet l'inférence sur WSI. Il écrit un fichier
intermédiaire `*.partial.csv` pendant le traitement d'une lame, puis le renomme
en `*_probs.csv` lorsque l'inférence est complète. Cette stratégie permet la
reprise après interruption avec l'option `--resume`, point important compte
tenu de la durée de calcul sur CPU.

Des heatmaps peuvent ensuite être générées avec `src/07_visualize_heatmap.py`.
Elles permettent une visualisation spatiale des zones suspectes et constituent
un support de revue anatomopathologique.

### Décision au niveau WSI

Les prédictions patch-level sont agrégées en décision au niveau de la lame par
une règle de composante connexe. Pour un seuil de probabilité donné, les patches
dont la probabilité tumorale dépasse ce seuil sont considérés comme positifs.
La plus grande composante connexe de patches positifs est ensuite mesurée. Une
lame est classée positive si cette composante atteint une taille minimale.

Cette approche vise à limiter l'impact des faux positifs isolés, fréquents dans
les WSI normales. Les paramètres explorés comprennent :

- des seuils de probabilité patch-level de 0,5 à 0,9 ;
- des tailles minimales de composantes allant de 10 à 200 patches.

Une règle interprétable initialement retenue était :

```text
probabilité patch >= 0,5
taille minimale de composante connexe >= 40 patches
```

Les performances WSI-level sont évaluées par sensibilité, spécificité,
précision, F1-score, vrais positifs, faux positifs, faux négatifs et vrais
négatifs.

### Analyse des faux positifs et hard-mining

Les premières évaluations ont montré que des lames normales pouvaient contenir
des clusters de patches à forte probabilité tumorale. Ces faux positifs ont été
analysés selon deux modalités :

- micro-clusters très suspects, utiles comme mode d'alerte mais insuffisamment
  spécifiques pour une décision automatique ;
- grandes composantes faussement positives, candidates au hard-negative mining.

Les composantes faussement positives sont extraites sous forme de patches et de
contact sheets, puis relues visuellement. La revue utilise un outil clavier
permettant d'attribuer une catégorie morphologique et une décision d'inclusion
comme hard negative.

Les catégories de revue incluent notamment :

- sinus histiocytosis ;
- macrophage/histiocyte ;
- fibrosis/stroma benign ;
- vessel/lumen ;
- electrocoagulation artifact ;
- benign necrosis/coagulation ;
- generic artifact ;
- benign but not useful ;
- uncertain/review later ;
- reject/uninformative.

Pour la prochaine phase de revue, le protocole prévoit une lecture indépendante
par un junior puis par un pathologiste senior, suivie d'une comparaison des
accords et d'une discussion de consensus. Les décisions initiales ne doivent
pas être écrasées par le consensus.

### Itération `iter6`

L'itération `iter6` a été construite à partir du jeu d'entraînement `iter2`,
auquel ont été ajoutés 120 patches hard negatives issus de 15 composantes
faussement positives revues. Ces composantes provenaient de cinq lames normales
d'entraînement : `normal_011`, `normal_022`, `normal_025`, `normal_028` et
`normal_032`.

Les catégories ajoutées étaient :

| Catégorie | Patches ajoutés |
| --- | ---: |
| electrocoagulation artifact | 24 |
| fibrosis/stroma benign | 16 |
| sinus_histiocytosis | 48 |
| vessel/lumen | 32 |

Le dataset `iter6` contient 732 patches normaux et 287 patches tumoraux, soit
1019 patches au total. Après entraînement, `iter6` atteint sur le jeu de
validation patch-level une précision tumorale de 0,967, un rappel de 1,000 et
un F1-score de 0,983, identiques aux performances tumorales précédemment
observées pour `iter2` sur ce même jeu de validation. Ce résultat suggère que
l'ajout des hard negatives n'a pas dégradé la sensibilité patch-level.

L'évaluation WSI-level d'`iter6` reste nécessaire pour déterminer si ces hard
negatives améliorent effectivement la spécificité sur lame entière.

### Évaluation prévue sur lames du service

À terme, le pipeline sera appliqué à des lames numérisées issues du service,
afin d'évaluer sa transférabilité hors du jeu CAMELYON16. Cette étape permettra
d'étudier l'effet des conditions locales : scanner, coloration, préparation des
tissus, distribution des cas et artefacts propres au workflow du laboratoire.

L'évaluation sur données locales devra être organisée avec une séparation
stricte entre les lames utilisées pour le développement, la sélection des
seuils et l'évaluation finale. Selon la disponibilité des annotations, la
référence pourra reposer sur le diagnostic anatomopathologique, une relecture
ciblée des régions suspectes et/ou des annotations manuelles de zones
métastatiques.

### Comparaison future avec UNI et Virchow

La comparaison avec UNI et Virchow constituera une étape ultérieure. Ces
modèles fondationnels pourront être utilisés comme extracteurs de
caractéristiques de patches ou de tuiles WSI. Les représentations obtenues
pourront ensuite alimenter un classifieur supervisé léger ou un modèle
d'agrégation au niveau lame.

La comparaison devra porter non seulement sur les métriques de performance,
mais aussi sur :

- la quantité d'annotation nécessaire ;
- la robustesse aux variations locales ;
- la capacité à réduire les faux positifs ;
- la détection des petites métastases ;
- les contraintes matérielles ;
- la lisibilité des sorties pour le pathologiste.

## Références à importer dans Zotero

Clés provisoires à harmoniser avec l'export Zotero :

- `@whoBreastCancer2026` : WHO breast cancer fact sheet.
- `@globocanBreastCancer2022` : GLOBOCAN 2022 / Global Cancer Observatory.
- `@incaCancerSein2026` : INCa, Les cancers du sein.
- `@spfCancerSein2025` : Santé publique France, cancer du sein, données.
- `@rapportNumerisationACP2025` : rapport ministériel sur la numérisation de
  l'anatomie et cytologie pathologiques.
- `@ehteshamiBejnordiCamelyon2017` : Ehteshami Bejnordi et al., JAMA 2017,
  CAMELYON16.
- `@aiLymphNodeMetastasesReview2023` : systematic review on AI for lymph node
  metastases.
- `@solimanBreastAI2024` : Artificial intelligence's impact on breast cancer
  pathology.
- `@katayamaBreastPathologyAI2024` : Current status and prospects of AI in
  breast cancer pathology.
- `@digitalPathologyRoutineReview2024` : Implementation of digital pathology and
  AI in routine pathology practice.
- `@chenUNI2024` : Chen et al., UNI, Nature Medicine 2024.
- `@vorontsovVirchow2024` : Virchow foundation model, Nature Medicine 2024.
