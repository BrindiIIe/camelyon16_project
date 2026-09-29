# Introduction, méthodes et résultats préliminaires

*Version de travail — 29 septembre 2026*

## Titre de travail

Comparaison d'un algorithme supervisé et des modèles fondationnels UNI et
Virchow pour la détection de métastases ganglionnaires mammaires sur les lames
histologiques numérisées du service.

## Fil conducteur

Ce travail s'inscrit dans le déploiement récent de la pathologie numérique au
sein du service d'anatomie et cytologie pathologiques. Son objectif principal
est de comparer, sur des lames issues du service, un algorithme supervisé
développé localement aux modèles fondationnels UNI et Virchow pour la détection
de métastases ganglionnaires mammaires.

La première étape, présentée ici, est une phase préparatoire. Elle consiste à
construire sur le jeu public CAMELYON16 un algorithme supervisé de référence et
une chaîne d'évaluation complète : extraction de patches, apprentissage,
inférence sur lame entière, génération de cartes de probabilité, décision au
niveau de la lame et analyse morphologique des erreurs. Cette phase doit
aboutir à un protocole reproductible qui sera ensuite appliqué aux trois
modèles sur les données du service : notre modèle supervisé, UNI et Virchow.

## Introduction

### Cancer du sein et enjeu ganglionnaire

Le cancer du sein est le cancer le plus fréquent chez la femme dans le monde.
Selon les estimations les plus récentes relayées par l'Organisation mondiale de
la santé, environ 2,4 millions de femmes ont reçu un diagnostic de cancer du
sein et 694 000 en sont décédées dans le monde en 2024
[@whoBreastCancer2026]. En France, il constitue également le cancer le plus
fréquent chez la femme, avec 61 214 nouveaux cas estimés et 12 765 décès en
2023 selon l'Institut national du cancer [@incaCancerSein2026]. Santé publique
France rapporte une augmentation de l'incidence depuis 1990, contrastant avec
une diminution de la mortalité, dans un contexte d'évolution du dépistage, des
pratiques diagnostiques et des traitements [@spfCancerSein2026].

Le statut ganglionnaire reste un élément majeur de la stadification et de la
prise en charge des cancers du sein. La présence de métastases dans les
ganglions lymphatiques influence le pronostic, l'indication de traitements
adjuvants et l'évaluation du risque de récidive. Son analyse repose sur
l'examen anatomopathologique de lames histologiques, tâche qui peut être longue
et répétitive lorsque de nombreux ganglions doivent être examinés, avec un
enjeu particulier pour les petites lésions, notamment les micrométastases et
les cellules tumorales isolées [@aiLymphNodeMetastasesReview2023].

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

Dans le service où s'inscrit ce travail, la numérisation récente des lames crée
une opportunité méthodologique : sous réserve du cadre réglementaire et de
l'anonymisation des données, les lames numériques pourront être utilisées pour
évaluer des algorithmes dans des conditions proches de la pratique réelle et
préparer l'intégration raisonnée d'outils d'aide au diagnostic.

### Intelligence artificielle en pathologie mammaire

L'intelligence artificielle appliquée aux WSI a montré des résultats
prometteurs dans plusieurs tâches de pathologie mammaire : détection de zones
tumorales, évaluation de biomarqueurs, quantification de l'expression HER2,
grading, détection de mitoses et identification de métastases ganglionnaires
[@solimanBreastAI2024; @katayamaBreastPathologyAI2024]. Le challenge
CAMELYON16 a constitué une étape importante pour l'évaluation de systèmes
d'apprentissage profond capables de détecter les métastases ganglionnaires
mammaires sur lames entières [@ehteshamiBejnordiCamelyon2017]. Dans le cadre
expérimental du challenge, certains algorithmes ont atteint des performances de
niveau comparable à celles de pathologistes, selon la tâche considérée et les
conditions de lecture, notamment la présence ou non d'une contrainte de temps.

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

La question principale est de déterminer, sur les lames ganglionnaires
numérisées du service, quelle stratégie offre le meilleur compromis pour la
détection de métastases mammaires : l'algorithme supervisé local, initialisé à
partir d'un ResNet18 pré-entraîné sur ImageNet puis entraîné sur CAMELYON16, ou
une approche fondée sur les représentations d'UNI ou de Virchow.

L'hypothèse principale est qu'UNI et Virchow, pré-entraînés sur de grandes
collections d'images histologiques, pourraient mieux s'adapter aux lames du
service que notre modèle supervisé, initialement pré-entraîné sur des images
non médicales. Cette hypothèse sera testée en comparant notre modèle supervisé
à UNI et à Virchow sur les mêmes lames, avec la même référence
anatomopathologique et les mêmes critères d'évaluation. Une meilleure
performance d'UNI ou de Virchow ne peut pas être supposée sur la seule base de
leur taille ou du volume de leurs données d'entraînement.

L'objectif principal est de comparer notre modèle supervisé à UNI et à Virchow
sur une même cohorte de lames du service et selon une même référence
anatomopathologique. La comparaison portera en priorité sur la performance au
niveau de la lame,
notamment la sensibilité et la spécificité, avec des règles de décision et un
jeu d'évaluation définis avant l'analyse finale.

Le développement sur CAMELYON16 constitue l'objectif méthodologique
préparatoire. Il vise à établir l'algorithme supervisé de référence, à fiabiliser
la chaîne d'analyse WSI et à définir les procédures de contrôle qui seront
appliquées aux données locales.

Les objectifs secondaires sont :

- constituer une cohorte locale rétrospective avec une séparation stricte des
  données de développement et d'évaluation ;
- entraîner et comparer plusieurs itérations du classifieur supervisé afin de
  figer la référence locale avant la comparaison principale ;
- adapter UNI et Virchow à la détection des métastases ganglionnaires afin de
  pouvoir les comparer équitablement à notre modèle supervisé sur les lames du
  service ;
- comparer les trois modèles au niveau patch et au niveau WSI, ainsi que leur
  comportement sur les petites lésions ;
- caractériser les faux positifs et faux négatifs par une revue morphologique ;
- décrire les contraintes pratiques de chaque modèle, notamment les besoins en
  annotation et en ressources informatiques, ainsi que la facilité
  d'interprétation de leurs résultats.

## Méthodes

### Type d'étude

Il s'agit d'une étude méthodologique rétrospective en deux phases. La première
phase utilise le jeu public CAMELYON16 pour développer l'algorithme supervisé
de référence et sécuriser la chaîne complète allant de la lame entière à une
décision interprétable au niveau WSI. Ce jeu fournit des WSI annotées, des
contours tumoraux XML et un cadre de comparaison établi dans la littérature.

La seconde phase constituera l'étude principale. Elle comparera l'algorithme
supervisé local, UNI et Virchow sur une cohorte de lames ganglionnaires
numérisées dans le service. Les trois modèles devront être évalués sur les
mêmes cas, avec la même référence anatomopathologique et une séparation des
données empêchant toute fuite entre adaptation, sélection des seuils et
évaluation finale.

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
l'exploration, la revue visuelle ou l'enrichissement ciblé ont été forcées dans le
split d'entraînement et exclues du test final.

Le split actuel est :

| Split | Normales | Tumorales | Total |
| --- | ---: | ---: | ---: |
| Entraînement | 126 | 86 | 212 |
| Validation | 29 | 19 | 48 |
| Test final | 79 | 46 | 125 |

Le groupe `test_final` est maintenu strictement à l'écart du développement et
aucun résultat final n'en est actuellement rapporté. Sa répartition provisoire
repose sur la présence d'une annotation XML pour identifier les lames
tumorales. Cette convention devra être confrontée aux métadonnées officielles
CAMELYON16 avant toute ouverture et toute analyse définitive du test.

### Prétraitement et extraction de patches

Afin de limiter l'analyse aux régions contenant du tissu, une image de faible
résolution de chaque lame est d'abord segmentée par la méthode d'Otsu. Le masque
obtenu est ensuite corrigé par plusieurs opérations morphologiques afin
d'éliminer les petites imperfections et de mieux délimiter les régions
tissulaires. Les patches sont uniquement extraits dans les zones retenues par
ce masque.

Une erreur dans la sélection du masque tissulaire a été identifiée au cours du
développement. Elle a été corrigée, et l'ensemble des résultats présentés dans
ce travail a été recalculé avec la méthode corrigée.

Des patches RGB de 256 × 256 pixels sont extraits au niveau de résolution
maximal de la lame. Les annotations XML des lames tumorales sont utilisées pour
attribuer un label tumoral ou normal selon la position du patch par rapport aux
régions annotées. Les patches sont redimensionnés à 224 × 224 pixels avant leur
entrée dans le réseau.

Les scripts principaux utilisés pour cette étape sont :

- `src/tissue_utils.py` pour les fonctions d'extraction ;
- `src/02_split_dataset.py` pour la constitution du split initial au niveau patch ;
- `src/build_train_dataset.py` et les scripts de préparation itérative pour les
  enrichissements successifs.

### Modèle supervisé au niveau patch

Le modèle supervisé repose sur un réseau ResNet18 préalablement entraîné sur
ImageNet, puis adapté pour classer chaque patch comme tumoral ou non tumoral.
Il a ensuite été entraîné sur les patches annotés de CAMELYON16. Des
modifications aléatoires de l'orientation, de la luminosité et du contraste des
images ont été appliquées pendant l'entraînement afin d'améliorer sa capacité à
reconnaître des tissus présentant des aspects légèrement différents.

Les principaux paramètres d'entraînement sont résumés ci-dessous :

| Paramètre | Valeur |
| --- | ---: |
| Optimiseur | Adam |
| Taux d'apprentissage | 10⁻⁴ |
| Taille des lots | 32 patches |
| Nombre d'époques | 10 |
| Graine aléatoire | 42 |

Le meilleur checkpoint est sélectionné sur le F1 tumoral du jeu de validation
patch, sans utiliser les lames du test final. Plusieurs itérations ont été
entraînées afin d'étudier l'effet d'un enrichissement progressif par cas
difficiles.

Les principales itérations sont :

- `baseline` : modèle initial ;
- `iter1`, `iter2`, `iter3` : enrichissements progressifs précoces ;
- `iter4` : ajout de micro faux positifs revus comme hard negatives ;
- `iter5` : ajout de faux positifs d'`iter4` et de hard positives ;
- `iter6` : retour à la base `iter2` avec ajout de 120 hard negatives issus
  de faux positifs WSI revus sur des lames d'entraînement ;
- `iter7` : ajout cumulatif de 136 hard negatives issus de 37 composantes
  relues après correction du masque tissulaire ;
- `iter8` : ajout cumulatif de 516 hard negatives issus d'un criblage stratifié
  de nouvelles lames normales d'entraînement.

Le modèle `iter2` reste le comparateur historique. `Iter7` et `iter8` permettent
d'étudier le compromis entre sensibilité et spécificité induit par
l'enrichissement en hard negatives. Les modèles sont jugés prioritairement sur
la validation WSI, les performances au niveau patch ne reflétant pas à elles
seules l'usage clinique visé.

### Inférence sur lame entière

L'inférence WSI repose sur un balayage du masque tissulaire nettoyé par patches
de 256 × 256 pixels, avec un pas de 128 pixels. Pour chaque position, le modèle
estime une probabilité tumorale. Les résultats sont stockés dans des fichiers
CSV contenant les coordonnées `x`, `y` et la probabilité tumorale.

Le script `src/05_infer_wsi.py` permet l'inférence sur WSI. Il écrit un fichier
intermédiaire `*.partial.csv` pendant le traitement d'une lame, puis le renomme
en `*_probs.csv` lorsque l'inférence est complète. Cette stratégie permet la
reprise après interruption avec l'option `--resume`, point important compte
tenu de la durée de calcul sur CPU.

Des cartes de probabilité peuvent ensuite être générées avec
`src/07_visualize_heatmap.py`. Elles permettent une visualisation spatiale des
zones suspectes et constituent un support de revue anatomopathologique.

### Décision au niveau WSI

Les prédictions au niveau patch sont agrégées en décision au niveau de la lame par
une règle de composante connexe. Pour un seuil de probabilité donné, les patches
dont la probabilité tumorale dépasse ce seuil sont considérés comme positifs.
La plus grande composante connexe de patches positifs est ensuite mesurée. Une
lame est classée positive si cette composante atteint une taille minimale.

Cette approche vise à limiter l'impact des faux positifs isolés, fréquents dans
les WSI normales. Sur le jeu de validation uniquement, les paramètres explorés
comprennent :

- des seuils de probabilité au niveau patch de 0,5 à 0,9 ;
- des tailles minimales de composantes allant de 20 à 1 000 patches.

La règle principale a été fixée avant l'analyse complète du jeu de validation :

```text
probabilité patch >= 0,5
taille minimale de composante connexe >= 40 patches
```

Les performances au niveau WSI sont évaluées par sensibilité, spécificité,
précision, F1-score, vrais positifs, faux positifs, faux négatifs et vrais
négatifs. Le jeu `test_final` ne sera ouvert qu'après gel du modèle et de cette
règle de décision.

### Analyse des faux positifs et enrichissement par cas difficiles

Les premières évaluations ont montré que des lames normales pouvaient contenir
des clusters de patches à forte probabilité tumorale. Ces faux positifs ont été
analysés selon deux modalités :

- micro-clusters très suspects, utiles comme mode d'alerte mais insuffisamment
  spécifiques pour une décision automatique ;
- grandes composantes faussement positives, candidates au hard-negative mining.

Les composantes faussement positives sont extraites sous forme de patches et de
planches contact, puis relues visuellement. La revue utilise un outil dédié
permettant d'attribuer un label binaire, une catégorie morphologique, un type
de difficulté et une décision d'inclusion comme hard negative.

Les catégories de revue incluent notamment :

- histiocytose sinusale (`sinus_histiocytosis`) ;
- macrophages/histiocytes ;
- fibrose ou stroma bénin (`fibrosis_stroma_benign`) ;
- vaisseau ou lumière (`vessel_lumen`) ;
- artefact d'électrocoagulation ;
- nécrose ou coagulation bénigne ;
- autre artefact ;
- tissu bénin non informatif ;
- cas incertain ou non interprétable.

Le protocole prévoit une lecture indépendante par un médecin junior et un
pathologiste senior, suivie d'une comparaison des accords et d'une discussion
de consensus. Les lectures initiales sont figées dans des fichiers distincts
et ne sont jamais remplacées par le consensus. Les faux positifs du jeu de
validation peuvent être examinés à visée diagnostique, mais ne sont jamais
réinjectés dans l'entraînement.

### Construction d'`iter6`, d'`iter7` et d'`iter8`

L'itération `iter6` a été construite à partir du jeu d'entraînement `iter2`,
auquel ont été ajoutés 120 patches hard negatives issus de 15 composantes
faussement positives revues sur cinq WSI normales du split d'entraînement.
Elle contient 732 patches normaux et 287 patches tumoraux.

Après correction du masque tissulaire, 37 nouvelles composantes bénignes ont
été retenues sur quatre autres WSI normales d'entraînement : `normal_033`,
`normal_034`, `normal_036` et `normal_037`. L'itération `iter7` reprend
cumulativement `iter6` et ajoute 136 patches, avec un maximum de quatre patches
par composante et de 64 nouveaux patches par WSI. Le jeu `iter7` contient ainsi
868 patches normaux et 287 patches tumoraux, soit 1 155 patches au total.

Pour ce lot corrigé, la décision finale a été obtenue après remise en contexte
WSI et adjudication. Le fichier de lecture senior indépendante étant resté
incomplet, la comparaison disponible doit être décrite comme junior versus
consensus adjudiqué, et non comme une mesure indépendante junior versus senior.

Pour `iter8`, un second criblage a porté sur 40 WSI normales d'entraînement,
réparties sur la plage `normal_024` à `normal_156` et sans recouvrement avec le
jeu de validation ou le test final. La revue a porté sur 133 composantes issues
de 31 lames ; 129 composantes ont été retenues par consensus. Quatre patches au
maximum ont été sélectionnés par composante, avec un plafond de 64 nouveaux
patches par lame. Après contrôle des doublons par coordonnées et empreinte
SHA-256, 516 hard negatives provenant de 30 lames ont été ajoutés à `iter7`.

Le jeu `iter8` contient 1 384 patches normaux et 287 patches tumoraux, soit
1 671 patches. Aucun hard positive supplémentaire n'a été ajouté. Le jeu de
validation patch est resté inchangé, de même que les splits WSI. Ce choix
permet d'isoler l'effet d'un enrichissement négatif important, mais expose à un
déséquilibre accru entre les classes.

## Résultats préliminaires

Les résultats présentés dans cette section concernent exclusivement la phase
préparatoire conduite sur CAMELYON16. Ils décrivent la construction du
comparateur supervisé et ne répondent pas encore à l'objectif principal de la
thèse, qui sera évalué par la comparaison directe de ce modèle avec UNI et
Virchow sur les lames du service.

### Validation au niveau patch

`Iter7` et `iter8` ont chacun été entraînés pendant 10 époques et évalués sur
le même jeu de validation de 218 patches, avec un seuil tumoral de 0,2. Les
matrices de confusion sont résumées ci-dessous.

| Modèle | VN | FP | FN | VP | Précision tumorale | Rappel tumoral | F1 tumoral |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `iter7` | 189 | 0 | 0 | 29 | 1,000 | 1,000 | 1,000 |
| `iter8` | 189 | 0 | 1 | 28 | 1,000 | 0,966 | 0,982 |

La validation patch suggère une dégradation limitée après l'enrichissement
`iter8`, avec un faux négatif supplémentaire. Elle ne prédit toutefois pas
l'ampleur du changement observé au niveau de la lame entière.

### Validation au niveau WSI

L'inférence des deux modèles a été réalisée sur les mêmes 48 WSI du split de
validation, soit 29 lames normales et 19 lames tumorales, avec le masque
tissulaire corrigé. Avec la règle principale fixée à un seuil patch de 0,5 et
une composante minimale de 40 patches, les résultats sont les suivants :

| Modèle | Sensibilité | Spécificité | Précision | F1 | Exactitude | VP | FP | FN | VN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `iter7` | 0,842 | 0,448 | 0,500 | 0,627 | 0,604 | 16 | 16 | 3 | 13 |
| `iter8` | 0,579 | 0,966 | 0,917 | 0,710 | 0,813 | 11 | 1 | 8 | 28 |

L'enrichissement d'`iter8` réduit ainsi les faux positifs de 16 à 1, mais
augmente les faux négatifs de 3 à 8. Il améliore la spécificité et l'exactitude
globales au prix d'une baisse importante de sensibilité ; il ne constitue donc
pas une amélioration clinique univoque.

Une grille exploratoire plus large, limitée à la validation, retrouve avec
`iter8` une sensibilité de 0,842 et une spécificité de 0,621 pour un seuil patch
de 0,3 et une composante minimale de 10 patches. Des règles plus sensibles
existent, mais leur spécificité diminue fortement : 0,947/0,414 pour la règle
0,15/2 et 1,000/0,276 pour la règle 0,25/1. Ces points de fonctionnement ont été
sélectionnés sur le jeu de validation et ne constituent pas des estimations de
performance finale.

### Analyse des pertes de sensibilité

La comparaison spatiale avec les annotations XML montre qu'à la règle 0,5/40,
la perte de signal tumoral localisé concerne principalement `tumor_071`,
`tumor_074` et `tumor_096`. Le nombre de centres annotés positifs à un seuil de
0,5 passe respectivement de 1 952 à 1, de 499 à 171 et de 542 à 0 entre
`iter7` et `iter8`. Cette analyse repose sur l'appartenance du centre des
patches aux polygones tumoraux ; elle ne mesure ni la surface de recouvrement ni
la sensibilité par lésion.

Une revue histologique ciblée de 36 sites a été préparée sur ces trois lames :
dix zones présentant les plus fortes chutes de probabilité et deux zones de
signal résiduel maximal par lame. Cette revue vise à identifier les motifs
tumoraux devenus difficiles après l'enrichissement négatif. Les lames
appartiennent à la validation : elles peuvent guider l'hypothèse expérimentale,
mais leurs patches ne seront pas intégrés à l'entraînement.

### Interprétation provisoire et étape suivante

Les résultats montrent que le hard-negative mining est efficace pour corriger
les faux positifs bénins ciblés, mais qu'un ajout massif de négatifs sans apport
tumoral parallèle peut déplacer excessivement la frontière de décision. La
prochaine expérience devra donc tester un enrichissement équilibré : maintien
des hard negatives déjà validés, ajout de hard positives provenant uniquement
des WSI d'entraînement et/ou rééquilibrage de l'exposition aux classes pendant
l'apprentissage. Cette expérience devra être comparée à `iter7` et `iter8` sur
le même jeu de validation et selon une règle WSI définie à l'avance.

La taille limitée du jeu de validation, la sélection exploratoire de règles sur
ce même jeu et l'absence actuelle d'évaluation externe imposent une
interprétation prudente. Le jeu `test_final` reste fermé jusqu'au gel du modèle
et de la règle de décision. Une fois ce comparateur supervisé figé, le travail
principal portera sur l'évaluation comparative locale ; les itérations sur
CAMELYON16 constituent donc un moyen de stabiliser le protocole, et non la
finalité de la thèse.

### Étude comparative principale sur les lames du service

L'étude principale sera conduite sur des lames ganglionnaires numérisées issues
du service. Elle évaluera la capacité de l'algorithme supervisé à fonctionner
sur des données différentes de CAMELYON16 et le comparera directement à UNI et
Virchow dans les conditions techniques locales : scanner, coloration,
préparation des tissus, distribution des cas et artefacts propres au
laboratoire.

UNI et Virchow devront être adaptés à la détection des métastases
ganglionnaires, car ils ne fournissent pas directement une décision diagnostique
pour cette tâche. Le protocole précisera comment leurs résultats seront obtenus
au niveau de chaque zone puis combinés au niveau de la lame. Notre modèle
supervisé, UNI et Virchow seront évalués sur les mêmes données, avec la même
référence anatomopathologique et les mêmes critères de performance.

La cohorte locale devra être séparée entre adaptation, validation et évaluation
finale. Selon la disponibilité des annotations, la référence reposera sur le
diagnostic anatomopathologique, complété par une relecture ciblée des régions
suspectes et, lorsque nécessaire, par des annotations manuelles des zones
métastatiques.

Le critère principal sera défini au niveau de la lame. La sensibilité et la
spécificité seront rapportées pour chaque modèle, accompagnées des matrices
de confusion et d'intervalles de confiance. Les analyses secondaires porteront
sur la détection des petites métastases et la morphologie des erreurs. Les
besoins en annotation et en ressources informatiques, ainsi que la facilité
d'interprétation des résultats, seront également décrits pour chaque modèle.

## Bibliographie de travail

Les clés suivantes sont provisoires et devront être harmonisées avec l'export
Zotero avant mise en forme définitive :

- `@whoBreastCancer2026` : Organisation mondiale de la santé, *Breast
  cancer*, mise à jour du 3 juillet 2026.
- `@incaCancerSein2026` : Institut national du cancer, *Les cancers du sein*,
  mise à jour du 22 juillet 2026.
- `@spfCancerSein2026` : Santé publique France, *Cancer du sein — Données*,
  mise à jour du 6 juillet 2026.
- `@rapportNumerisationACP2025` : rapport ministériel sur la numérisation de
  l'anatomie et cytologie pathologiques.
- `@ehteshamiBejnordiCamelyon2017` : Ehteshami Bejnordi et al., JAMA 2017,
  CAMELYON16.
- `@aiLymphNodeMetastasesReview2023` : revue systématique sur l'IA et les
  métastases ganglionnaires.
- `@solimanBreastAI2024` : Soliman et al., *Artificial intelligence's impact
  on breast cancer pathology*, Diagnostic Pathology, 2024.
- `@katayamaBreastPathologyAI2024` : Katayama et al., *Current status and
  prospects of artificial intelligence in breast cancer pathology*,
  International Journal of Clinical Oncology, 2024.
- `@digitalPathologyRoutineReview2024` : *Implementation of digital pathology
  and artificial intelligence in routine pathology practice*, Laboratory
  Investigation, 2024.
- `@chenUNI2024` : Chen et al., UNI, Nature Medicine 2024.
- `@vorontsovVirchow2024` : Vorontsov et al., Virchow, Nature Medicine 2024.
