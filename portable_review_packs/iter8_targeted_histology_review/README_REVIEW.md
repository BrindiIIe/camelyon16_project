# Revue histologique ciblée Iter8

Ce pack documente la perte de signal localisée entre Iter7 et Iter8 sur
`tumor_071`, `tumor_074` et `tumor_096`. Il contient 36 sites de revue
(tumor_071: 12, tumor_074: 12, tumor_096: 12).

## Utilisation

1. Ouvrir `review.html` dans Chrome, Edge ou Firefox.
2. Examiner d'abord la vue d'ensemble de la lame, puis chaque planche.
3. Renseigner les quatre décisions et, si nécessaire, les notes.
4. Cliquer sur **Exporter le CSV**. Le fichier téléchargé est
   `review_completed.csv`.

La saisie intermédiaire est conservée dans le stockage local du navigateur.
`review_template.csv` contient les mêmes sites avec des colonnes vierges si une
revue dans un tableur est préférable.

## Échantillonnage

Pour chaque lame, dix sites tumoraux annotés sont choisis parmi les plus fortes
chutes de probabilité Iter7→Iter8, avec espacement spatial. Deux sites
supplémentaires correspondent au meilleur signal Iter8 restant et servent de
contrôles internes. Le carré cyan indique le patch exact de 256 px vu par le
modèle. Les contours rouges sont les annotations Tumor et les contours orange
les Exclusion.

## Garde-fou expérimental

Ces trois lames appartiennent à la validation. Les images du pack servent
uniquement à comprendre l'échec et à définir une expérience sur les données
d'entraînement. Elles ne doivent jamais être copiées dans un dataset de train.
Le jeu `test_final` n'est pas utilisé.
