# Was die Messungen gesagt haben

> Die „Neins" waren nützlicher als das „Ja".

Vier Fragen wurden der trainierten Fliege gestellt. Drei kamen als „nein"
zurück, und genau die haben sich gelohnt.

---

## 1. Hilft mehr Training? Nein.

Der Darbietungs-Recall auf Track-Ebene liegt bei 0,429: die Fliege legt sich bei
9 von 21 zurückgehaltenen Positiven fest. Die naheliegende Lesart ist, dass sie
mehr Epochen braucht.

Braucht sie nicht. Jeder einzelne der zwölf Fehlschläge hat einen Peak deutlich
über der Hälfte:

| zurückgehaltenes Positiv | Peak-Konfidenz |
|---|---|
| studio-1987 (×5 Uploads) | 0,99 |
| tv-countdown-1987 | 0,98 |
| live-bbc-nye | 0,97 |
| pianoforte (×2) | 0,96 · 0,94 |
| live-2016 | 0,92 |
| live-late-late-show | 0,90 |
| live-foo-fighters | 0,88 |

Die mittlere Peak-Konfidenz über alle Fehlschläge ist **0,96**. Der Schaltkreis
erkennt diese Tracks Perzept für Perzept. Was versagt, ist der Dopamin-Pool
darüber, der seine Schwelle nie überschreitet. Mehr Epochen können keine
Schwelle verschieben.

`docs/img/misses.png` zeichnet das: die blasse Linie ist, was der Schaltkreis
geglaubt hat, die durchgezogene der Pool, die gestrichelte die Latte.

## 2. Hilft eine andere Commit-Regel? Nein.

Die Commit-Regel ist ein Leaky Integrator mit drei freien Zahlen
(Zeitkonstante, tonische Grundlinie, Schwelle), durchgefahren über 252
Kombinationen. Ein naheliegender Verdacht ist, dass die *Form* falsch ist und
nicht die Zahlen.

Eine zweite Familie wurde auf denselben Out-of-Fold-Spuren getestet: **N der
letzten M Perzepte über einem Schnitt**, 210 Kombinationen, eine Ratenregel
statt eines Integrators. Unter identischen Randbedingungen:

| Regelfamilie | bester Darbietungs-Recall | bei Upload-Spezifität |
|---|---|---|
| Leaky Integrator (aktuell) | **0,429** | 0,977 |
| N-von-M | 0,238 | 0,955 |

Der Integrator gewinnt, und zwar deutlich. `docs/img/commitment.png` zeigt den
weiteren Punkt: unter allen Regeln, die den Spezifitätsboden schaffen, hat die
bereits gewählte den höchsten Darbietungs-Recall. Der Tuner lässt nichts liegen.

## 3. Was ist dann die Grenze? Drei falsche Alarme.

Die Regel ist an 0,95 Spezifität auf zurückgehaltenen Uploads gebunden, bevor
Recall überhaupt angeschaut wird. Vier Negative reißen sie, und drei davon sind
derselbe Künstler:

```
astley-whenever    Rick Astley - Whenever You Need Somebody        bei  9,5 s
astley-whenever    Rick Astley - Whenever You Need Somebody (JP)   bei  9,5 s
astley-she-wants   Rick Astley - She Wants To Dance With Me        bei 64,1 s
speech-ted         TED - How not to be ignorant about the world    bei 12,0 s
```

Denselben Sweep ohne die Astley-Negative:

| | bester Darbietungs-Recall |
|---|---|
| wie gemessen | 0,429 |
| ohne die Astley-Negative | **0,762** |

Diese drei Tracks kosten **0,333 Darbietungs-Recall**. Die Fliege hatte
teilweise *Stock Aitken Waterman, 1987, diese Stimme* gelernt statt *diesen
Song*.

## 4. Helfen mehr harte Negative? Nein, und das ist der wichtige Befund.

Der Korpus trug bereits 19 harte Negative: neun Rick-Astley-Singles, sechs
weitere Stock-Aitken-Waterman-Produktionen, und einen anderen Song, der zufällig
denselben Titel trägt. Vierzehn weitere kamen dazu: je vier zusätzliche Uploads
der beiden Tracks, bei denen die Fliege messbar mit dem Ziel durcheinanderkommt,
plus Mel & Kim, Sinitta, Jason Donovan und Kylie Minogue.

**Das Training scheiterte.** Keine Commit-Regel im Sweep erreicht den
0,95-Spezifitätsboden noch. Das Beste, was erreichbar ist, sind **0,897**.

Alle Negative nach dem Anteil ihrer Perzepte über der Hälfte sortiert:

| Track | über 0,5 | |
|---|---|---|
| She Wants To Dance With Me (HQ) | **99,2 %** | neu |
| She Wants To Dance With Me (2023 Remaster) | 91,5 % | neu |
| She Wants To Dance With Me (Musikvideo) | 89,5 % | neu |
| She Wants To Dance With Me (Top Of The Pops) | 89,2 % | neu |
| *bestes echtes Positiv (Karaoke)* | *88,3 %* | |
| She Wants To Dance With Me (ursprünglicher Eintrag) | 70,4 % | |
| *mittleres echtes Positiv* | *50,4 %* | |

Die Fliege ist sich **sicherer, dass „She Wants To Dance With Me" der Rickroll
ist, als bei jedem echten Rickroll im Korpus.**

Der naheliegende Fehler wurde zuerst geprüft. Ein Negativ, das das Ziel heimlich
enthält, würde das Training vergiften, und genau das verbieten die
Kurations-Regeln. Daran liegt es nicht: alle vier neuen Uploads laufen 196 bis
199 s gegen die 3:19 der Single, keiner ist eine Compilation, und ausgerechnet
der vorbestehende Eintrag desselben Songs ist der untypische, nämlich 259 s und
damit eine Minute länger als die anderen.

Der Schluss ist unerfreulich und gehört klar hingeschrieben: **die 0,977
Spezifität, die das Modell meldet, war durch dünne Abdeckung seines nächsten
Verwechslungskandidaten geschönt.** Ein Upload von „She Wants To Dance With Me"
war im Korpus, und es war zufällig ein ungewöhnlicher. Mit vier gewöhnlichen
zeigt sich die echte Trennschärfe, und die ist deutlich schlechter.

Die vierzehn Tracks liegen im Manifest unter `use: "holdout"`. Sie werden
geladen und bleiben reproduzierbar, aber es wird nicht auf ihnen trainiert, denn
sie zu übernehmen heißt den Spezifitätsboden zu senken, und dieser Boden ist ein
Produktversprechen und kein Hyperparameter.

---

## 5. Hilft ein längeres Perzept? Nein, und es kostet den größten Teil des Recalls.

Die naheliegende Lesart von Befund 4 ist, dass 801 ms zu kurz sind: über
anderthalb Schläge sind zwei Stock-Aitken-Waterman-Singles fast dasselbe Objekt,
und was sie trennt, ist Melodie und harmonische Bewegung. Also wurde das Fenster
verdoppelt: `subframes` 3 → 6, ein Perzept von 1,567 s, etwa drei Schläge. Die
Klauen gingen mit 20 → 40, weil sich die Rezeptorschicht verdoppelt hat und das
eigene Argument der Config lautet, dass das *Verhältnis* den Hash trägt. Sie bei
20 zu lassen hätte das Abtastverhältnis auf 5,6 % halbiert und die beiden
Änderungen vermischt.

Auf Perzept-Ebene ein Nullsummenspiel. Auf Track-Ebene eine Katastrophe.

| | 0,801 s | 1,567 s |
|---|---|---|
| Darbietung macro AUC | 0,7038 | 0,7014 |
| Darbietung gepoolt AUC | 0,7804 | 0,7627 |
| **Darbietung Track-Recall** | **0,429** | **0,095** |
| Darbietung Track-Spezifität | 0,909 | 0,932 |
| Upload macro AUC | 0,9714 | 0,9756 |
| Upload Recall / Spezifität | 1,000 / 0,977 | 1,000 / 0,977 |
| erster Verdacht (Upload) | 0,8 s | 2,6 s |

**Gefangene zurückgehaltene Positive: 9 von 21 → 2 von 21.** Übrig bleiben nur
`extended-mix` und `karaoke`.

Und auf dem harten Korpus hilft es überhaupt nicht: die beste erreichbare
Upload-Spezifität geht **0,897 → 0,879**, also leicht schlechter als das kurze
Fenster.

Die Fold-Tabelle sagt warum, und es ist kein Rauschen. Die Folds bewegen sich
konsistent in entgegengesetzte Richtungen:

| Darbietungs-Fold | 0,801 s | 1,567 s | |
|---|---|---|---|
| live-foo-fighters | 0,752 | **0,857** | rauf |
| live-bbc-nye | 0,703 | **0,774** | rauf |
| karaoke | 0,891 | **0,933** | rauf |
| extended-mix | 0,939 | **0,957** | rauf |
| studio-1987 | **0,903** | 0,879 | runter |
| tv-countdown-1987 | **0,656** | 0,578 | runter |
| pianoforte | **0,467** | 0,369 | runter |
| live-2016 | **0,329** | 0,262 | runter |

Die Deutung, die passt: **ein längeres Fenster ist starrer gegenüber dem
Tempo.** Drei Schläge einer Aufnahme mit leicht anderem Tempo laufen aus der
Deckung mit dem, was die Fliege gelernt hat; anderthalb Schläge driften halb so
weit. Das breitere Perzept ist die bessere Schablone für *dieselbe Aufnahme*
(jeder Upload-Fold wurde besser, die Upload-AUC stieg) und die schlechtere für
*eine andere Darbietung desselben Songs*, also für genau das, was besser werden
sollte.

Das ist das Gegenteil des beabsichtigten Effekts, also wurde die Änderung
zurückgenommen. Sie steht hier, weil es ein Experiment ist, das man aus Versehen
wiederholt.

Es schließt außerdem die Rahmung aus. Das Problem ist nicht, dass das Fenster zu
kurz für die Melodie ist. Tempo-Starrheit und Klangfarben-Verwechslung sind
dieselbe Beschwerde aus zwei Richtungen: die Repräsentation hängt an der
*Oberfläche* einer bestimmten Aufnahme statt an dem, was der Song ist. Das
Fenster zu verlängern schiebt sie weiter in diese Richtung, nicht heraus.

---

## 6. Der Meme-Fall: der Pool hat die falsche Form für einen Vier-Sekunden-Sting

Ein echtes Meme, eingeworfen: `hB7CDrVnNCs`, fünfzehn Sekunden lang, die Platte
von 11 s bis 15 s hineingeschnitten. Die App sagte **kein Rickroll**, und sie
war dabei nicht nahe am Raten:

```
erster Verdacht  10,89 s      Peak-Konfidenz  0,965
Peak-Dopamin      0,474   vs   Schwelle  0,60
```

Das Video ging ihr auf 79 Prozent des Weges zur Überzeugung aus. Der Pool
braucht rund zehn Sekunden Song, das Meme trug vier. Das ist keine seltene Form:
die meisten Rickrolls da draußen sind die ersten fünf bis fünfzehn Sekunden der
Platte, hinten an etwas anderes getackert.

**Dafür kam ein zweiter Commit-Pfad**: zwei Sekunden mit mindestens 0,93
mittlerer Konfidenz, in einer Aufnahme von höchstens 25 Sekunden. Drei Dinge
machten ihn vertretbar.

*Die Auswertungsmenge musste erst gebaut werden.* Jedes Negativ im Manifest ist
ein ganzer Track, eine Regel für Fünfzehn-Sekunden-Memes hatte also noch nie ein
Fünfzehn-Sekunden-Nicht-Meme gesehen. Rund neuntausend kurze negative Clips
wurden aus den Out-of-Fold-Spuren geschnitten, und Memes wurden so simuliert, wie
Memes gemacht werden: Füllmaterial, dann ein paar Sekunden Platte.

*Spezifität fällt mit der Länge, und das ist das ganze Argument für die
Schranke.* Eine gleitende Regel bekommt pro Perzept eine Chance zu feuern, ein
Vier-Minuten-Track gibt ihr also fast zweitausend und ein
Fünfzehn-Sekunden-Clip etwa hundert:

| Clip-Länge | 15 s | 25 s | 45 s | 60 s | 120 s |
|---|---|---|---|---|---|
| Spezifität | 96,3 % | 95,1 % | 93,4 % | 92,4 % | 90,0 % |

Ungeschränkt drückt dieser Pfad die Upload-Spezifität von 0,977 auf 0,909 und
bricht den Boden. Bei 25 s geschränkt erreicht er einen Track voller Länge gar
nicht, also bleibt jede Schlagzeilenzahl unverändert (Upload 1,000 / 0,977,
Darbietung 0,429 / 0,909, weiterhin alles über den Pool festgelegt), während
kurze Videos eine Regel bekommen, die auf ihrer eigenen Population an dieselbe
0,95 gebunden ist.

*Was er bringt.* Auf simulierten Vier-Sekunden-Stings steigt der Recall von
**39,8 % auf 67,5 %**. Ende zu Ende legt sich das Video oben jetzt bei 13,7 s
fest, und die Platte, die Werbung, das gewöhnliche Negativ und das harte
Astley-Negativ verhalten sich genau wie vorher.

Zwei Vorbehalte, festgehalten statt begraben. Die Schwelle ist 0,93 und dieses
Video kommt über seine besten zwei Sekunden auf 0,934, ein Abstand von vier
Tausendsteln. Der Schnitt ist damit ebenso sehr an dieses eine Beispiel gefittet
wie an den Sweep. Und ein langes Video mit kurzem Sting wird weiterhin
konstruktionsbedingt verfehlt: die Schranke ist die Aussage, dass ein
Vier-Minuten-Upload vom Pool beurteilt wird, egal was hineingeschnitten ist.

### 6b. Der erste Vorbehalt trat ein, und der Sweep war nicht reproduzierbar

Zwei gewöhnliche Acht-Sekunden-Rickrolls, *Rick Roll (Different link + no ads)*
und *Rick roll, but with different link*, also genau die Form, für die es diese
Regel gibt, kommen über ihre besten zwei Sekunden auf **0,9202** und **0,9269**.
Beide wurden als *kein Rickroll* gemeldet, während die Fliege zu 97 Prozent
überzeugt war und der Pool bei 0,39 gegen 0,60 stehenblieb. Eine Schwelle, vier
Tausendstel über einem Beispiel gefittet, verfehlte die nächsten zwei Beispiele,
die ihr begegneten.

Schlimmer: der Sweep, der 0,93 hervorgebracht hat, wurde nie eingecheckt, die
Zahl war also nicht bestreitbar. `frrf-commitment` baut ihn jetzt aus
`models/traces.npz` nach: Memes geschnitten als Füller-dann-Sting aus der
**Upload**-Familie, kurze Negative aus gewöhnlichen Tracks in denselben Längen.

Beim Nachbauen kam etwas heraus, das die ursprüngliche Notiz falsch hatte. **Der
Burst-Pfad feuert kaum.** Von 0,99 bis 0,86 gegen neuntausend
Out-of-Fold-Kurznegative durchgefahren, sind die gemessenen Kosten bei jedem
Schritt *null* zusätzliche Fehlalarme, weil der Pool jeden kurzen Clip, den der
Burst fangen würde, schon von selbst festgelegt hat. Fehlalarme beginnen bei
0,84, wo fünfzehn auftauchen. Der behauptete Sprung von 39,8 auf 67,5 Prozent
reproduziert sich nicht: auf dieser Population nimmt der Pool allein 95 bis 100
Prozent der simulierten Memes, und die echte Aufgabe des Bursts ist das schmale
Band, in dem der Pool steckenbleibt. Genau dort saßen jene beiden Videos.

Der Schnitt wanderte also auf **0,90**: sechs Hundertstel über der Kante des
flachen Bereichs statt vier Tausendstel über einem Beispiel. Auf echtem Audio
ist die Änderung chirurgisch.

| Video | vorher | nachher |
|---|---|---|
| Rick Roll, no ads (8 s) | nie | **4,0 s** |
| Rick roll, different link (7 s) | nie | **4,0 s** |
| Send this to all your friends (15 s) | 13,7 s | 13,1 s |
| die Platte (213 s) | 9,5 s | 9,5 s |
| Versicherungswerbung (65 s) | 4,6 s | 4,6 s |
| Astley-Hartnegativ (208 s) | nie | nie |
| drei gewöhnliche Negative | nie | nie |

Das Hartnegativ ist der Grund, warum die 25-Sekunden-Schranke nicht ebenfalls
zur Verhandlung steht: seine besten zwei Sekunden mitteln **0,9479**, bequem
über dem neuen Schnitt, und nur seine Länge hält den Burst davon fern.

Ein Fall bleibt verfehlt und bleibt es: *10 rickrolls 1 video*, 34 Sekunden,
außerhalb der Schranke, mit besten zwei Sekunden von nur 0,855. Die Schranke
bleibt die Aussage, dass alles jenseits von 25 Sekunden Sache des Pools ist.

Zwei Messungen, die festzuhalten sich lohnt, solange der Sweep existierte. Die
Kurzclip-Spezifität ist **0,86**, weit unter den 0,977, die die Fliege auf
ganzen Tracks hält: fünfzehn Prozent zufälliger Fünf- bis
Fünfundzwanzig-Sekunden-Fenster gewöhnlicher Negative legen sich fest, über den
Pool, bei vollständig abgeschaltetem Burst. Das ist eine vorbestehende Schwäche
des Pools auf kurzen Eingaben und hat mit dieser Regel nichts zu tun. Und die
Familie, aus der der Sting eines Memes geschnitten wird, ändert die Antwort
vollständig: aus `rendition` geschnitten sind simulierte Memes so schwer, dass
nichts feuert; aus `upload` geschnitten nimmt der Pool fast alle. Wer einen
Rickroll-Link einwirft, wirft einen Upload ein, also ist `upload` die
Population, und das zu sagen gehört zur Behauptung dazu.

### 6c. Die Schranke war die falsche Variable, und die Statistik die falsche Statistik

Der Vorbehalt am Ende von Befund 6, *ein langes Video mit kurzem Sting wird
weiterhin konstruktionsbedingt verfehlt*, ist kein Randfall. Es ist die
häufigste Form, die ein Rickroll annimmt: vier Sekunden Platte, vergraben in
zehn Minuten von etwas anderem. Eingeworfen: ein Elf-Minuten-Video mit **1,3 s
und 1,4 s** Song. Peak-Konfidenz 0,976, Pool bei 0,471 gegen 0,60 hängen
geblieben, Burst durch die 25-Sekunden-Schranke aus. **Kein Rickroll.**

Der naheliegende Fix ist, den Burst zu entsperren. Das funktioniert nicht, und
die Messung ist nicht knapp. Bestes Zwei-Sekunden-Mittel über ganze Tracks, ohne
Schranke:

| | bestes 2-s-Mittel |
|---|---|
| TED-Talk, *How not to be ignorant about the world* | **0,985** |
| *She Wants To Dance With Me* (das Hartnegativ) | **0,972** |
| das Elf-Minuten-Video, das wirklich ein Rickroll ist | 0,939 |

Nach dieser Statistik sortiert verliert der echte Rickroll gegen einen Vortrag.
Ein Mittel über ein Fenster kann von einem einzigen Ausschlag getragen werden,
und ein langes Video bietet tausende Fenster, in denen sich einer findet. Die
Schranke schützte keine willkürliche Längengrenze, sie schützte eine Statistik,
die viele Versuche nicht übersteht.

**Eine ungebrochene Serie übersteht sie.** Zu verlangen, dass *jedes*
aufeinanderfolgende Perzept eine hohe Latte nimmt, ist ein viel härterer Test,
weil er jedes abgedeckte Perzept überleben muss statt über sie zu mitteln. Von
vierundvierzig Negativen in voller Länge hält genau eines 0,97 über sechs
Zehntelsekunden, und es ist *She Wants To Dance With Me*, von dem dieses Projekt
ohnehin dokumentiert, dass die Fliege es teilweise mit dem Song verwechselt.

Also ein dritter Pfad, ungeschränkt: **0,97, gehalten über 0,60 s.** Gemessen
auf den Out-of-Fold-Tracks:

| | Recall | Spezifität |
|---|---|---|
| unbekannter Upload | 1,000 → 1,000 | 0,977 → **0,977** |
| unbekannte Darbietung | 0,429 → **0,619** | 0,909 → **0,909** |

Keine der beiden Spezifitäten bewegt sich. Der Darbietungs-Recall, die ehrliche
Zahl, steigt um neunzehn Punkte, weil ein Cover, das kurz richtig liegt, jetzt
zählt, auch wenn sein Pool nie lädt. Das Elf-Minuten-Video legt sich bei 163,8 s
fest, beim zweiten Auftreten des Songs.

Drei Dinge festgehalten statt begraben. Die Latte steht an einer Kante: bei
0,60 s liegt die Upload-Spezifität bei 0,977, bei 0,50 s bei 0,909, und das
Video, mit dem das verfolgt wurde, hält 0,97 über 0,639 s. Ein Abstand von sechs
Prozent, besser als die vier Tausendstel, die die erste Burst-Regel versenkt
haben, aber immer noch ein Abstand. Der neue Recall ist langsamer: der mittlere
Darbietungs-Commit geht von 28,1 s auf 41,9 s und p90 von 50,6 s auf 190,5 s,
weil nichts bereits Gefangenes schneller wurde und alles neu Gefangene schwer
und spät ist. Und *10 rickrolls 1 video*, 34 Sekunden, wird weiterhin verfehlt,
seine beste Serie hält 0,97 nie so lange.

### 6d. Die Defaults in `brain/config.py` sind nicht die ausgelieferte Fliege

Beim Messen des Obigen gefunden, und mehr wert als eine Fußnote. Das Training
tunt die Commit-Parameter und legt die gewählten ins Modell, also:

| | `brain/config.py` | `models/fly_brain.npz` |
|---|---|---|
| `da_tau` | 0,9 | **2,0** |
| `da_baseline` | 0,66 | **0,72** |
| `da_commit` | 0,35 | **0,6** |

Das ist so beabsichtigt, der Docstring der Dataclass sagt, dass die Config mit
den Gewichten reist. Für alles, was Verhalten misst, ist es trotzdem eine Falle.
Ein Sweep auf einer nackten `BrainConfig()` reproduziert eine Upload-Spezifität
von **0,614**, wo die ausgelieferte Fliege **0,977** erreicht, und jeder daraus
gezogene Schluss handelt von einem Tier, das nie ausgeliefert wurde. Die
früheren Kurzclip-Zahlen in 6b wurden so berechnet und sind nur als Hinweis zu
lesen; die Echtaudio-Tabelle in 6b nicht, die steht. Der Docstring von
`BrainConfig` sagt das jetzt ausdrücklich: die Config aus
`FlyBrain.load(...).config` nehmen, nie aus den Defaults.

## 7. Die Fliege kann zusehen, und es hilft nicht

Die Frage war, ob man die Fliege dazu bringen kann, das Video zu *sehen* statt
nur zu hören. Die Antwort ist, dass der Pfad funktioniert, die Biologie stimmt,
und die Fliege fast nichts daraus lernt.

**Was gebaut wurde.** Ein Drosophila-Auge hat etwa 750 Ommatidien, ein Bild wird
also zu einem hexagonalen 32×24-Raster, und kein Wünschen holt daraus ein
Gesicht. Worin Fliegen außergewöhnlich sind, ist Zeit: die Flimmerfusion liegt
nahe 200 Hz gegen unsere sechzig. Also ist der Pfad ein Bewegungspfad, und zwar
der aus dem Lehrbuch: Ommatidien speisen Reichardt-Korrelatoren (ein verzögertes
Signal einer Facette, multipliziert mit dem unverzögerten der Nachbarin, minus
dem Spiegelbild dieses Produkts), und die werden in zwölf tangentiale
Weitfeldzellen gepoolt, die für die Lobula-Platte stehen. Zwölf Felder, je vier
Richtungen, plus zwölf Flimmerkanäle sind sechzig pro Bild. Die Zahl des Ohrs,
mit Absicht, damit drei Sub-Frames in beiden Fällen 180 Rezeptoren ergeben und
dieselbe Calyx beide Sinne lesen kann.

**Was es erreicht hat.** Gepoolte Out-of-Fold-Perzept-AUC, gleiche Folds,
gleicher Schaltkreis, alles gleich außer dem Sinn:

| | Darbietung | unbekannter Upload |
|---|---|---|
| Ohr | **0,780** | **0,971** |
| Auge | 0,621 | 0,631 |

Über dem Münzwurf, und nicht annähernd genug. `frrf-train` hat **sich geweigert,
überhaupt eine sehende Fliege auszuliefern**: keine Commit-Regel erreicht auch
nur einen Spezifitätsboden von 0,70 bei vollem Upload-Recall, was die eigene
Schutzvorrichtung des Trainers ist, die genau wie vorgesehen arbeitet.
`models/fly_eye.npz` existiert nicht und die Anwendung ist unverändert.

**Zwei Dinge, die der Versuch zutage gefördert hat und die die Reise wert
waren.**

*Sehr viele Uploads sind Fotografien.* Achtunddreißig Prozent der Positiven in
diesem Korpus sind ein Standbild mit Audio dahinter, gegen sechzehn Prozent der
Negativen. In diesem Korpus ist **ein Standbild zu sein also mit dem Ziel
korreliert**: P(positiv | statisch) = 0,53 gegen eine Grundrate von 0,32. Jedes
Video an seiner eigenen Spitzenaktivität zu normalisieren machte aus dem
Kompressionsflimmern dieser Fotos etwas, das wie Choreografie aussah, und der
Schaltkreis hätte diese Korrelation lernen und darauf punkten können. Das ist
eine Tatsache darüber, wie der Korpus gesammelt wurde, und keine über den Song.
Das Auge schränkt jetzt darauf ein, wie sicher es ist, dass sich überhaupt etwas
bewegt hat: ein Foto liest 0,00000, wo ein Musikvideo 0,03 liest.

*Einen zweiten Sinn zu trainieren fand eine stille Korruption im ersten.*
`load_times` las das Standard-Feature-Verzeichnis, egal was `load_corpus`
bekommen hatte, also paarte das Training auf Sicht die Konfidenzen des Auges mit
der Uhr des Ohrs. Es ist hier zufällig abgestürzt, weil die beiden
unterschiedlich viele Perzepte haben. Hätten sie übereingestimmt, wäre lautlos
ein plausibles und vollständig falsches Modell entstanden.

**Warum es nicht funktioniert, soweit die Messung reicht.** Die
Bewegungsstatistik eines Popvideos von 1987 unterscheidet sich bei zwölf
Weitfeldkanälen und dreißig Bildern pro Sekunde nicht sehr von der anderer
Popvideos. Der eine Fold, der gut läuft, `extended-mix` mit AUC 0,948, ist ein
Visualizer mit markantem Stroboskop, also erkennt der Pfad einen Upload und
nicht den Song. Das ist derselbe Fehlschlag, den das Ohr hat, und Sehen macht
ihn schlimmer: in einem Klaviercover kommt gar kein Rick Astley vor, Sicht kann
dem Darbietungsfall also nicht helfen, und der ist der tatsächlich schwache.

Trotzdem behalten: `brain/eye.py`, `frrf-watch` und `models/traces-eye.npz`,
denn ein negatives Ergebnis ist nur etwas wert, wenn die Evidenz dafür wieder
lesbar ist.

---

## Worauf das hindeutet

Nicht auf mehr Daten und nicht auf eine bessere Entscheidungsregel. Auf die
Repräsentation.

Das Perzept sind 801 ms aus 48 Mel-Bändern und 12 Tonklassen. Über dieses
Fenster sind zwei Stock-Aitken-Waterman-Singles, im selben Studio im selben Jahr
mit derselben Stimme geschnitten, fast dasselbe Objekt: gleicher Tempobereich,
gleicher Drumcomputer, gleiche Synth-Patches, gleiche Stimme. Was sie trennt,
ist Melodie und Harmoniefolge, und dafür braucht es entweder mehr Gewicht auf
dem Chroma-Kanal oder ein längeres Fenster als anderthalb Schläge.

Daraus folgen vier Experimente, von denen keines neues Audio braucht:

1. ~~**Ein längeres Perzept.**~~ Versucht, in Befund 5. Es macht die Fliege zum
   besseren Schablonenabgleicher für eine Aufnahme und zum schlechteren
   Erkenner des Songs.
2. **Chroma gegen Mel**, jetzt der aussichtsreichste Kandidat. Die
   Verstärkungsregelung normalisiert die beiden Bänke ohnehin getrennt, sie
   lassen sich also neu gewichten, ohne das Ohr anzufassen. Eine Nur-Chroma- und
   eine Nur-Mel-Fliege zu trainieren würde direkt sagen, welche Bank die
   Astley-Verwechslung trägt. Die Erwartung aus Befund 5 ist, dass Mel
   (Klangfarbe, Produktion, die Oberfläche der Aufnahme) die meiste Arbeit tut,
   und genau das ist der Teil, den zwei im selben Studio im selben Jahr
   geschnittene Singles gemeinsam haben.
3. **Tempo-Invarianz.** Befund 5 hat gezeigt, dass die Repräsentation an einem
   Tempo hängt. Nichts im Modell normalisiert darauf. Sub-Frames könnten statt
   einer festen Anzahl *Frames* eine feste Anzahl *Schläge* umfassen. Das ist
   eine echte Änderung am Ohr und die größte einzelne Idee, die noch offen ist.
4. **Den harten Korpus mit ehrlichem Boden übernehmen.** Auf allen 79 Tracks
   trainieren mit `--with-holdout --min-specificity 0.85` und die niedrigeren
   Zahlen melden, mit der Begründung, dass sie die wahren sind.

Jede der obigen Messungen nachzuvollziehen braucht nur `models/traces.npz`, die
Out-of-Fold-Konfidenzverläufe, und kein erneutes Training.

<details>
<summary>🇬🇧 English</summary>

Four questions were asked of the trained fly. Three came back "no", and the
"no"s were the useful part.

**1. More training does not help.** Rendition track recall is 0.429 (9 of 21),
but the twelve misses have a mean *peak* confidence of 0.96. The circuit
recognises them percept by percept; the dopamine pool on top never crosses. More
epochs cannot move a threshold.

**2. A different commit rule does not help.** A leaky integrator (252
combinations) against an N-of-M rate rule (210): 0.429 at 0.977 specificity
against 0.238 at 0.955. The integrator wins comfortably, and the tuner is
already picking the best rule available to it.

**3. The constraint is three false positives.** Two uploads of *Whenever You
Need Somebody*, one of *She Wants To Dance With Me*, and a TED talk. Removing
the Astley negatives takes rendition recall 0.429 → 0.762. Those three tracks
cost 0.333 of recall: the fly has partly learned *Stock Aitken Waterman, 1987,
that voice* rather than *this song*.

**4. More hard negatives make it worse, and this is the important one.** Adding
fourteen (including four ordinary uploads of *She Wants To Dance With Me*) puts
the specificity floor out of reach; the best available becomes 0.897. The fly is
*more* confident that *She Wants To Dance With Me* is the Rickroll than it is
about any real Rickroll in the corpus (99.2 % of percepts over half, against
88.3 % for the best true positive). The 0.977 the model reports was flattered by
thin coverage of its nearest confusable neighbour. Those tracks are carried at
`use: "holdout"`, because adopting them means lowering a floor that is a product
promise rather than a hyperparameter.

**5. A longer percept does not help and costs most of the recall.** Doubling the
window to 1.567 s is a wash at percept level and a disaster at track level:
rendition recall 0.429 → 0.095, 9 of 21 caught down to 2. The folds move in
opposite directions consistently, and the reading that fits is that a longer
window is more rigid about tempo. It is a better template for *the same
recording* and a worse recogniser of *the song*, which is the opposite of the
intent. Reverted, and written down because it is easy to repeat by accident.

**6. Three ways to commit.** The pool needs ~10 s of song and misses a
four-second meme sting. A burst path (2 s averaging 0.90, gated to clips of at
most 25 s) covers short memes; the gate is load-bearing because specificity
decays with length, and the hard negative's best two seconds average 0.9479. But
the gate then misses the commonest shape of all, four seconds buried in eleven
minutes. Ungating does not work: ranked by best two-second mean, a TED talk
(0.985) and the hard negative (0.972) both beat a real eleven-minute Rickroll
(0.939), because a mean can be carried by one spike and a long video supplies
thousands of windows to find one in. An unbroken run cannot. So a third,
ungated path: 0.97 held for 0.60 s. Rendition recall 0.429 → 0.619 with neither
specificity moving. Sub-findings record that the first burst threshold was
fitted four thousandths above a single example and promptly missed the next two,
that the sweep behind it was never committed and did not reproduce, and that
`brain/config.py`'s defaults are *not* the shipped fly (a sweep on a bare
`BrainConfig()` reports 0.614 where the real one scores 0.977).

**7. The fly can watch, and it does not help.** A full Reichardt motion pathway
scores 0.621 / 0.631 against the ear's 0.780 / 0.971, and `frrf-train` refused
to ship a visual fly at all. Two things were worth the trip: 38 % of the
positives here are still images against 16 % of negatives, so *being a
photograph is correlated with being the target* in this corpus, which the eye
now gates against; and training a second sense exposed a silent bug that paired
one sense's confidences with the other's clock.

**What it points at:** the representation, not the data or the rule. Next:
re-weighting chroma against mel, and tempo invariance (sub-frames of a fixed
number of *beats* rather than frames). Every measurement above is reproducible
from `models/traces.npz` with no retraining.

</details>

> Die Messungen, die nicht funktioniert haben, 2026.
