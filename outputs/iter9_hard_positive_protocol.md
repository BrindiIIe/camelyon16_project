# Protocole Iter9 d'enrichissement en hard positives

Gelé le 18 octobre 2026 avant l'extraction des candidats et avant toute
consultation des résultats du test final.

## Hypothèse

L'ajout de hard negatives dans `iter8` a fortement réduit les faux positifs,
mais la revue ciblée a confirmé la présence de tumeur dans 28 des 30 sites de
validation ayant perdu le plus de signal. Un enrichissement limité en hard
positives provenant exclusivement des WSI d'entraînement pourrait récupérer
ce signal tumoral et permettre une règle WSI plus spécifique tout en conservant
une sensibilité de 100 % sur la validation.

## Source des candidats

- modèle de criblage : `models/best_resnet18_patch_iter8.pt` ;
- empreinte SHA-256 attendue :
  `00c243996e6ea1ae402a4be709624f2d1a7a4d4e3f7d0d9a9c675f517b7b2eed` ;
- population : les 86 WSI tumorales du split `train` de
  `outputs/splits/wsi_split_v1.csv` ;
- exclusion stricte : aucune WSI de `val` ou de `test_final` ;
- grille : centres espacés de 256 pixels, patches de 256 pixels ;
- annotation : centre et quatre points situés à 96 pixels du centre tous dans
  un polygone `Tumor` et hors polygone `Exclusion` ;
- qualité minimale automatisée : au moins 50 % de pixels non blancs.

## Définition et sélection

- hard positive candidat : probabilité tumorale Iter8 strictement inférieure à
  0,25 ;
- classement : probabilité croissante ;
- espacement entre candidats d'une même lame : au moins 1 024 pixels ;
- maximum par WSI : 3 ;
- maximum global soumis à la revue : 120 ;
- allocation : un premier candidat par WSI avant un éventuel deuxième puis un
  troisième, afin de privilégier la diversité inter-lames.

## Revue et inclusion

Chaque candidat doit être revu sur le patch central et son contexte. Il ne sera
inclus que si la tumeur est confirmée, si l'image est interprétable et si la
confiance est moyenne ou élevée. Les cas bénins, incertains, non évaluables ou
principalement expliqués par un bord d'annotation seront exclus.

`iter9` sera construit à partir de `data/patches_iter8/train` en ajoutant
uniquement les hard positives acceptés. Aucun nouveau hard negative ne sera
ajouté. Le protocole d'entraînement restera identique à celui d'`iter8` afin
d'isoler l'effet de l'enrichissement positif.

## Critère de réussite

La règle WSI sera choisie sur la même grille de validation que pour le gel du
comparateur supervisé. `iter9` sera considéré comme amélioré uniquement s'il :

1. détecte les 19 WSI tumorales de validation sur 19 ;
2. obtient une spécificité strictement supérieure à 0,276 sous cette contrainte.

En l'absence d'amélioration, aucune nouvelle itération CAMELYON16 ne sera
entreprise. Les sorties même partielles de `test_final` ne seront utilisées ni
pour sélectionner les hard positives, ni pour entraîner, régler ou choisir
`iter9`.
