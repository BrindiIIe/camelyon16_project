# Synthèse de la revue junior ciblée — 17 octobre 2026

## Statut et traçabilité

- Source conservée sans modification : `review_completed_legacy_2026-10-17.csv`.
- Formulaire utilisé : `review.html`, première version du formulaire.
- Échantillon : 36 sites, soit 12 sites sur chacune des lames `tumor_071`,
  `tumor_074` et `tumor_096`.
- Complétude : 36 diagnostics centraux, 36 motifs dominants, 36 mécanismes
  proposés et 36 niveaux de priorité.
- Contrôle des identifiants : aucun site manquant, supplémentaire ou dupliqué
  par rapport au pack.
- Métadonnées à compléter : le lecteur n'est renseigné sur aucune ligne et la
  date manque sur une ligne. Les 35 autres lignes portent la date du
  17 octobre 2026.

Cette lecture reste une revue junior indépendante et préliminaire. Elle ne
constitue ni une lecture senior ni un consensus.

## Résultat principal

Parmi les 30 sites sélectionnés pour la plus forte chute de probabilité entre
Iter7 et Iter8, 28 contiennent de la tumeur au centre du patch (93,3 %) et 2
n'en contiennent pas. Les six sites de contrôle correspondant au meilleur
signal Iter8 restant contiennent tous de la tumeur.

La perte de signal observée sur ces lames ne paraît donc pas s'expliquer
principalement par une sélection de patches hors tumeur. Elle concerne le plus
souvent des patches effectivement tumoraux. Cette conclusion porte uniquement
sur cet échantillon ciblé de cas extrêmes et ne mesure pas la sensibilité
globale du modèle.

## Synthèse par lame

| Lame | Tumeur au centre | Motifs dominants | Mécanismes les plus souvent proposés | Priorité haute |
|---|---:|---|---|---:|
| `tumor_071` | 12/12 | Métastase cohésive 6/12 ; nécrose 2/12 ; autres motifs dispersés | Mécanisme incertain 4/12 ; nécrose 3/12 ; décalage d'exposition des classes 2/12 | 6/12 |
| `tumor_074` | 11/12 | Métastase cohésive 5/12 ; bord d'annotation 4/12 | Annotation ou échantillonnage 7/12 ; faible fraction tumorale 2/12 | 4/12 |
| `tumor_096` | 11/12 | Fibrose ou desmoplasie 8/12 | Fibrose ou desmoplasie 9/12 ; annotation ou échantillonnage 3/12 | 2/12 |

Deux sites à forte chute ont été classés sans tumeur au centre :
`tumor_074_site_10` et `tumor_096_site_08`. Ils peuvent correspondre à un effet
de bord, d'échantillonnage ou à une très faible représentation tumorale et ne
doivent pas être interprétés comme des faux négatifs tumoraux certains.

## Lecture des motifs

Sur l'ensemble des 36 sites, les motifs dominants les plus fréquents sont la
métastase cohésive (12), la fibrose ou desmoplasie (10) et le bord d'annotation
(7). Les mécanismes proposés se concentrent sur la fibrose ou desmoplasie (11)
et l'annotation ou l'échantillonnage (11), devant les mécanismes incertains (5)
et la nécrose (4).

Le profil diffère nettement entre les lames. `tumor_096` fournit un signal
cohérent en faveur d'une difficulté liée au stroma fibreux ou desmoplasique.
`tumor_074` paraît davantage influencée par les limites d'annotation et la
faible quantité de tumeur dans certains patches. `tumor_071` reste plus
hétérogène : plusieurs patches montrent une tumeur cohésive, mais le mécanisme
de la perte est souvent incertain ou associé à la nécrose.

## Conséquence expérimentale

Cette revue justifie de tester séparément, sur les seules données
d'entraînement, des stratégies visant :

1. les zones tumorales dans un stroma fibreux ou desmoplasique ;
2. les faibles fractions tumorales et les petits amas ;
3. les effets de bord d'annotation et d'échantillonnage ;
4. les zones nécrotiques ou altérées.

Les patches de ces trois lames de validation servent à comprendre l'échec. Ils
ne doivent pas être ajoutés au jeu d'entraînement. Une éventuelle lecture
senior devra être réalisée indépendamment sur les mêmes sites avant toute
adjudication.
