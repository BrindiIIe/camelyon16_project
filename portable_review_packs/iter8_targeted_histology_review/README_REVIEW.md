# Revue histologique ciblée Iter8

Ce pack documente la perte de signal localisée entre Iter7 et Iter8 sur
`tumor_071`, `tumor_074` et `tumor_096`. Il contient 36 sites de revue
(tumor_071: 12, tumor_074: 12, tumor_096: 12).

## Utilisation

1. Ouvrir `review_junior.html` dans Chrome, Edge ou Firefox.
2. Renseigner le nom ou les initiales du lecteur et la date de lecture.
3. Examiner d'abord les vues d'ensemble, puis chaque planche.
4. Pour chaque site, renseigner les quatre champs obligatoires :
   - diagnostic du patch central ;
   - motif histologique dominant ;
   - qualité de l'image ;
   - niveau de confiance.
5. Ajouter si possible le mécanisme expliquant la perte de signal et un
   commentaire libre.
6. Cliquer sur **Exporter le CSV junior**. Le fichier téléchargé est nommé
   `iter8_targeted_histology_review_junior_YYYY-MM-DD.csv`.

La saisie intermédiaire est conservée automatiquement dans le stockage local
du navigateur. Le bouton **Prochain incomplet** permet de reprendre rapidement
la lecture. Les informations sur les probabilités Iter7 et Iter8 sont masquées
dans un encadré repliable de l'interface ; les planches conservent néanmoins
leurs métadonnées techniques pour assurer la traçabilité de la sélection.

`review_junior_template.csv` contient les mêmes sites et les mêmes colonnes avec
des réponses vierges si une revue dans un tableur est préférable. Le fichier
`review.html` correspond à la première version du formulaire et est conservé
uniquement pour assurer la traçabilité.

### Sur MacBook

Après avoir récupéré la branche GitHub, ouvrir le dossier
`portable_review_packs/iter8_targeted_histology_review` dans le Finder, puis
double-cliquer sur `review_junior.html`. Conserver le fichier HTML dans ce
dossier afin que les images restent accessibles. L'export CSV sera téléchargé
dans le dossier habituel des téléchargements du navigateur. Il est recommandé
d'en conserver une copie datée sans la modifier.

## Statut de la lecture

Le formulaire enregistre systématiquement :

- `review_role = junior` ;
- `review_status = independent_preliminary`.

L'export junior doit être conservé sans modification avant toute consultation
d'une lecture senior. Il ne constitue ni une lecture senior ni un consensus.

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
