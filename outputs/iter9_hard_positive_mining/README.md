# Criblage des hard positives Iter9

Le criblage utilise uniquement les WSI tumorales du split d'entraînement.
Aucune WSI de validation ou de test final n'est lue.

- WSI tumorales d'entraînement prévues : 86
- WSI traitées : 86
- centres annotés et informatifs scorés : 166562
- centres avec probabilité Iter8 < 0,25 : 101764
- candidats retenus pour revue : 120

| Lame | Centres scorés | Centres < 0,25 | Retenus |
|---|---:|---:|---:|
| `tumor_001` | 141 | 0 | 0 |
| `tumor_002` | 6 | 4 | 1 |
| `tumor_003` | 70 | 0 | 0 |
| `tumor_004` | 286 | 189 | 2 |
| `tumor_005` | 21 | 0 | 0 |
| `tumor_006` | 20 | 0 | 0 |
| `tumor_007` | 20 | 1 | 1 |
| `tumor_008` | 1 | 0 | 0 |
| `tumor_009` | 12612 | 4591 | 2 |
| `tumor_010` | 2 | 0 | 0 |
| `tumor_011` | 2832 | 544 | 2 |
| `tumor_012` | 13 | 12 | 1 |
| `tumor_013` | 76 | 3 | 1 |
| `tumor_015` | 134 | 21 | 1 |
| `tumor_018` | 629 | 45 | 2 |
| `tumor_019` | 41 | 25 | 1 |
| `tumor_021` | 284 | 17 | 1 |
| `tumor_023` | 16 | 0 | 0 |
| `tumor_024` | 7 | 2 | 1 |
| `tumor_025` | 1035 | 551 | 2 |
| `tumor_026` | 10814 | 1155 | 2 |
| `tumor_027` | 29 | 11 | 1 |
| `tumor_028` | 12 | 0 | 0 |
| `tumor_029` | 714 | 249 | 2 |
| `tumor_030` | 1 | 0 | 0 |
| `tumor_031` | 1411 | 33 | 2 |
| `tumor_032` | 30 | 5 | 1 |
| `tumor_033` | 1406 | 369 | 2 |
| `tumor_034` | 883 | 500 | 2 |
| `tumor_035` | 0 | 0 | 0 |
| `tumor_036` | 839 | 17 | 1 |
| `tumor_037` | 371 | 81 | 2 |
| `tumor_038` | 431 | 20 | 1 |
| `tumor_039` | 2687 | 456 | 2 |
| `tumor_041` | 15 | 0 | 0 |
| `tumor_042` | 635 | 8 | 1 |
| `tumor_044` | 15246 | 10832 | 2 |
| `tumor_045` | 139 | 10 | 1 |
| `tumor_046` | 12063 | 7423 | 2 |
| `tumor_047` | 8429 | 940 | 2 |
| `tumor_048` | 21 | 10 | 1 |
| `tumor_049` | 24 | 3 | 1 |
| `tumor_050` | 78 | 37 | 2 |
| `tumor_052` | 733 | 165 | 2 |
| `tumor_053` | 7 | 0 | 0 |
| `tumor_055` | 4020 | 916 | 2 |
| `tumor_057` | 3 | 0 | 0 |
| `tumor_058` | 5193 | 1158 | 2 |
| `tumor_059` | 2 | 0 | 0 |
| `tumor_060` | 3 | 0 | 0 |
| `tumor_061` | 942 | 624 | 2 |
| `tumor_063` | 10 | 1 | 1 |
| `tumor_065` | 17 | 2 | 1 |
| `tumor_068` | 3445 | 2342 | 2 |
| `tumor_069` | 101 | 70 | 2 |
| `tumor_070` | 3 | 0 | 0 |
| `tumor_072` | 1674 | 1658 | 2 |
| `tumor_073` | 111 | 111 | 2 |
| `tumor_075` | 454 | 426 | 2 |
| `tumor_076` | 34821 | 26251 | 2 |
| `tumor_077` | 99 | 99 | 2 |
| `tumor_078` | 13151 | 13107 | 2 |
| `tumor_079` | 246 | 219 | 2 |
| `tumor_080` | 39 | 39 | 2 |
| `tumor_082` | 3458 | 3458 | 2 |
| `tumor_083` | 622 | 615 | 2 |
| `tumor_084` | 384 | 384 | 2 |
| `tumor_085` | 6886 | 6626 | 2 |
| `tumor_086` | 8 | 8 | 2 |
| `tumor_087` | 31 | 31 | 2 |
| `tumor_088` | 2427 | 2382 | 2 |
| `tumor_091` | 617 | 617 | 2 |
| `tumor_097` | 7 | 7 | 2 |
| `tumor_098` | 1 | 1 | 1 |
| `tumor_099` | 66 | 65 | 2 |
| `tumor_100` | 65 | 65 | 2 |
| `tumor_101` | 2688 | 2680 | 2 |
| `tumor_102` | 4207 | 4205 | 2 |
| `tumor_103` | 12 | 11 | 2 |
| `tumor_104` | 1329 | 1315 | 2 |
| `tumor_105` | 1057 | 1056 | 2 |
| `tumor_106` | 544 | 509 | 2 |
| `tumor_107` | 44 | 44 | 2 |
| `tumor_108` | 833 | 749 | 2 |
| `tumor_109` | 1573 | 1572 | 2 |
| `tumor_111` | 105 | 12 | 1 |
