# Revue des hard positives Iter9

Ce pack contient **120 sites issus de 70 WSI tumorales du jeu
d'entraînement**. Iter8 leur attribue une probabilité tumorale inférieure à
0,25 malgré leur position au cœur d'une annotation tumorale.

## Faire la revue

1. Ouvrir `review.html` dans Chrome, Edge, Firefox ou Safari.
2. Examiner le contexte, le zoom et le patch exact pour chaque site.
3. Renseigner les cinq champs obligatoires.
4. Cliquer sur **Exporter le CSV** après avoir renseigné le lecteur et la date.
5. Copier le CSV téléchargé dans ce dossier sans le modifier.

La saisie est sauvegardée automatiquement dans le navigateur. Le bouton
**Prochain incomplet** permet de reprendre la lecture. `review_template.csv`
offre une solution de secours pour une lecture dans un tableur.

## Règle d'inclusion dans Iter9

Un patch ne sera accepté que si toutes ces conditions sont réunies :

- `site_diagnosis = tumor` ;
- `image_quality` vaut `good` ou `interpretable_with_limitations` ;
- `confidence` vaut `medium` ou `high` ;
- `dominant_pattern` n'est pas `annotation_edge` ;
- `include_as_hard_positive = yes`.

Les réponses incertaines, de faible confiance ou non évaluables resteront dans
la trace de revue mais ne seront pas ajoutées au jeu d'entraînement.

## Garde-fou expérimental

La sélection utilise uniquement les 86 WSI tumorales du split d'entraînement.
Chaque lame fournit au maximum trois sites espacés d'au moins 1024 px, avec un
maximum global de 120. Aucune donnée de validation ou de test final n'est
utilisée. Iter9 ajoutera uniquement les hard positives confirmés à Iter8 ;
aucun nouveau hard négatif ne sera ajouté.
