# Worauf die Fliege trainiert wurde

> Die Daten unter dem Argument.

Erzeugt von `frrf-insights` aus dem Manifest, den gecachten Perzepten und den
Out-of-Fold-Spuren. Nichts hier braucht das Netz oder ein erneutes Training.

`docs/FINDINGS.md` ist das Argument, das hier sind die Daten darunter.

## Der Korpus

66 Tracks, 66.866 Perzepte, davon
19.987 (30 %) der Song. Dieses Ungleichgewicht
wird über Gewichtung behandelt und nicht durch Wegwerfen, jedes negative
Perzept im Korpus wird also gesehen.

![Was die Fliege bekommen hat](img/corpus.png)

| Art | Tracks | Perzepte | Label |
|---|---|---|---|
| music | 20 | 22.977 | nicht der Song |
| hard | 19 | 15.925 | nicht der Song |
| studio | 13 | 10.855 | der Song |
| live | 5 | 5.111 | der Song |
| speech | 5 | 7.977 | nicht der Song |
| rework | 3 | 2.663 | der Song |
| mix | 1 | 1.358 | der Song |

Die Tracklänge reicht von 120 s bis 480 s, im Mittel 227 s. 6 Tracks wurden an der
Längenobergrenze des Korpus abgeschnitten.

**Folds gehen nach Gruppe, nicht nach Track.** Die 50 Gruppen gibt es,
damit zwei Uploads derselben Aufnahme nie über eine Fold-Grenze getrennt werden
können. Einen Track zurückzuhalten, während sein Zwilling im Training bleibt,
misst nichts. Die größten Gruppen sind `studio-1987` (13), `pianoforte` (2), `astley-together-forever` (2), `astley-whenever` (2), `saw-roadblock` (2).

## Was sie mit jedem einzelnen macht

![Jeder Track als Streuung](img/separation.png)

Ein Track ist nicht eine Zahl, und die Überlappung in der Mitte dieser Abbildung
ist das ganze Problem: die Fliege liegt bei den Negativen, die sie verfehlt,
nicht selbstbewusst daneben, sie ist *unsicher*, und bei mehreren Positiven ist
sie es auch.

Zwei Zeilen lohnen sich mit dem Auge zu suchen. **She Wants To Dance With Me**
(gleicher Künstler, gleiche Produzenten, gleiches Jahr) sitzt fast ganz oben,
über den meisten echten Positiven. Diese eine Zeile ist das
„sie hat Stock Aitken Waterman, 1987, diese Stimme gelernt"-Problem, das die
README einräumt. Und jede Live-Darbietung und das Klaviercover sitzen in der
unteren Hälfte, was die Darbietungs-Zahl von 0,6 statt 0,97 ist.

## Was die Kreuzvalidierung gefunden hat

| | Perzept-AUC | Track-Recall | Track-Spezifität | mittlerer Commit |
|---|---|---|---|---|
| unbekannte Darbietung | 0.704 macro · 0.780 gepoolt | 0.619 | 0.909 | 41.9 s |
| unbekannter Upload | 0.971 macro · 0.971 gepoolt | 1.000 | 0.977 | 10.0 s |

![ROC](img/roc.png)

![AUC pro Fold](img/folds.png)

Die Macro-Zahl verdeckt eine breite Streuung, und dafür ist die Fold-Abbildung
da.

## Was die Commit-Regel gekostet hat

![Was die Commit-Regel gekostet hat](img/commitment.png)

## Was sie weiterhin verfehlt

![Fehlschläge](img/misses.png)

## Hören gegen Sehen

![Hören gegen Sehen](img/senses.png)

Derselbe Schaltkreis, dieselben Folds, dieselben 180 Rezeptoren, nur der Sinn
ist anders. Sicht liegt knapp über der Diagonalen, und deshalb weigert sich
`frrf-train`, eine sehende Fliege auszuliefern, und deshalb gibt es kein
`models/fly_eye.npz`. Die Begründung ist Befund 7.

> Erzeugt, nicht geschrieben. `frrf-insights`.
