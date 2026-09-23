# Der Schaltkreis

> Was hier Fliege ist und was Engineering.

`brain/config.py` trägt die Zahlen, dieses Dokument die Begründung. Der Anspruch
des Projekts ist eng und soll genau so dastehen: **das ist ein Modell des
Pilzkörpers von Drosophila, angewendet auf Audio, und keine Fliege.** Der
Pilzkörper ist ein assoziativer Speicher, dessen Architektur ungewöhnlich gut
beschrieben ist (ein spärlicher Zufalls-Expander, ausgelesen von einer Handvoll
Ausgangsneuronen, mit Dopamin als Schreibsignal), und genau diese Architektur
wird nachgebaut. Das Ohr davor ist kein Fliegenohr, und was gelernt wird, ist
kein Geruch.

```
Ton ──► Johnston-Organ ──► Antennallobus ──► Kenyon-Zellen ──► MBONs ──► Dopamin-Pool ──► Urteil
        48 Mel + 12 Chroma  divisive        4.000 Zellen,     approach   leaky
        × 3 Sub-Frames      Verstärkung     200 feuern        avoidance  Integrator
        = 180 Rezeptoren                    (5 %)
```

Jede Stufe unten sagt, was die Fliege hat, was das Modell tut, und aus welcher
der beiden Quellen die Zahl kommt.

---

## 1. Johnston-Organ: das Ohr

**Die Fliege.** Drosophila hört mit den Antennen. Das Johnston-Organ enthält
rund 480 mechanosensorische Neuronen in fünf funktionalen Gruppen, abgestimmt
auf verschiedene Frequenzen der Antennenschwingung. Ein echter
Frequenzanalysator, und der Weg, auf dem eine Fliege einen Balzgesang hört.

**Das Modell.** Eine Mel-Filterbank, 48 Bänder von 40 Hz bis 8 kHz, gelesen als
tonotope Kanäle. Drei aufeinanderfolgende Sub-Frames von 255 ms ergeben ein
Perzept, die Fliege entscheidet also über 801 ms Ton. Etwa anderthalb Schläge
bei den 113 BPM des Zielsongs.

**Wo das vom Tier abweicht.** Die 12 Chroma-Bins sind *keine* Fliegenstruktur
und werden auch nicht als solche ausgegeben. Es sind Tonklassen, und sie
existieren, weil Harmonik das ist, was ein Klaviercover überlebt, während
Klangfarbe es nicht tut. Sie bekommen eine eigene, längere Transformation (4096
Punkte, 186 ms), weil bei dem 1024-Punkte-Fenster der Mel-Bänder ein Bin 21,5 Hz
breit ist. Das sind drei Halbtöne am unteren Ende des Bassbereichs, und die
Tonklassen dort unten kamen als Rauschen heraus. Gemessener Effekt der
Umstellung auf unbekannte Darbietungen: AUC 0,802 → 0,828.

---

## 2. Antennallobus: die Verstärkungsregelung

**Die Fliege.** Olsen, Bhandawat und Wilson zeigten 2010, dass der Ausgang eines
Projektionsneurons eine divisiv normalisierte Funktion seines Eingangs ist: jeder
Kanal wird durch das geteilt, was die ganze Population gerade tut. Die
Duftkonzentration schwankt über Größenordnungen, und so übersteht die
Repräsentation der Fliege das.

**Das Modell.** Dieselbe divisive Form, mit dem Exponenten aus dieser Arbeit.
Mel-Bänder normalisieren gegen Mel-Bänder, Tonklassen gegen Tonklassen, ein Pool
pro Sub-Frame. Es sind verschiedene Einheiten, und eine Amplitude durch eine
Größe in anderer Einheit zu teilen bedeutet nichts.

**Engineering, nicht Biologie.** `al_sigma` und `al_suppression` sind an den
Dynamikumfang von Musik angepasst, nicht an den von Gerüchen. Die
kanalweisen `gains` sind eine homöostatische Skalierung, einmalig aus dem
Trainingskorpus gefittet: tiefe Mel-Bänder tragen in jeder je gemachten Aufnahme
weit mehr Energie als hohe, und ohne diesen Ausgleich würde das obere Ende des
Spektrums nie eine Kenyon-Zelle gewinnen.

---

## 3. Kenyon-Zellen: der spärliche Zufalls-Expander

**Die Fliege.** Der Teil, für den es dieses Projekt gibt. Jede Kenyon-Zelle
bildet eine Handvoll dendritischer Klauen aus, und jede Klaue greift sich im
Wesentlichen zufällig ein Projektionsneuron. Niemand sucht aus, welches.
Dasgupta, Stevens und Navlakha zeigten (*Science*, 2017), dass das ein
lokalitätssensitiver Hash im formalen Sinn ist: ähnlicher Eingang, ähnliche
Gewinnermenge. Anschließend speist das APL-Neuron, eine einzelne Zelle die den
ganzen Lobus innerviert, Hemmung zurück und lässt nur wenige Prozent feuern.
Heraus kommt ein spärlicher binärer Tag: der Name, den die Fliege diesem
bestimmten Ton gibt.

**Das Modell.** 4.000 Kenyon-Zellen, 20 Klauen pro Zelle, 5 % bleiben
ungehemmt.

**Herkunft jeder Zahl.**

| Zahl | Wert | Woher sie kommt |
|---|---|---|
| Kenyon-Zellen | 4.000 | Das Konnektom zählt etwa 2.000 pro Hemisphäre, und eine Fliege hat zwei. Das ist ein ganzes Tier. Bringt 0,03 AUC gegenüber einer Hemisphäre, der beste Ertrag aller Parameter in der Datei, und der einzige, der sich allein mit „die Fliege hat wirklich so viele" rechtfertigt. |
| Klauen pro Zelle | 20 | Erhalten wird das *Verhältnis*, nicht die Anzahl. Eine Fliege bildet etwa 6 Klauen aus etwa 50 Projektionsneuronen, also 12 %; die Eingangsschicht hier ist größer, und 20 von 180 sind 11 %. Den absoluten Wert bei 6 zu halten kostet 0,03 AUC, weil 6 Klauen aus 180 zu wenig von einem Perzept sehen, um etwas zu sagen. |
| Sparsity | 5 % | Entspricht der gemessenen Spärlichkeit des echten Codes. Bei 2.000 Zellen schnitt ein lockereres 10 % besser ab; mit voller Population gewinnt die treue 5 %. Das zeigt sich nur, wenn man beides zusammen durchfährt. |
| Projektions-Seed | 1987 | Die Klauenziehung ist eingefroren, denn eine Fliege verdrahtet ihre Calyx nicht zwischen zwei Songs neu. Das Erscheinungsjahr des Songs. |

**Der schwächstbelegte Schritt im Modell.** Jede Zelle bekommt eine eigene
Feuerschwelle, gesetzt so, dass sie auf dem Trainingskorpus etwa 5 % der Zeit
gewinnt. Erregbarkeits-Homöostase ist für Neuronen allgemein gut belegt; für
Kenyon-Zellen speziell ist die Evidenz dünner. Der Schritt steht hier, weil die
Codequalität ohne ihn messbar schlechter ist: Klauen werden zufällig gezogen,
also greifen manche Zellen sechs laute Tiefenkanäle ab und gewinnen jeden
Wettbewerb, während andere nie feuern. Ein Code, in dem dieselben 1.150 Zellen
jeden Ton tragen, ist ein schlechter Code.

---

## 4. MBON-Kompartimente: wo die Erinnerung sitzt

**Die Fliege.** Die Loben des Pilzkörpers sind in Kompartimente geteilt, jedes
mit eigenem Ausgangsneuron und eigenen dopaminergen Neuronen. Jedes MBON drückt
das Verhalten in eine Richtung: hin zu der Sache oder weg von ihr. **Lernen ist
Subtraktion.** In einem Kompartiment freigesetztes Dopamin schwächt genau die
Kenyon-Zell-Synapsen, die gerade aktiv waren, also treibt ein erfahrener Geruch
die Antwort nicht mehr, die er vorher trieb. Eine Erinnerung ist ein Muster
geschwächter Synapsen und sonst nichts.

**Das Modell.** Zwei Kompartimente, `approach` und `avoidance`. Die Gewichte
starten auf einem Ruhewert, sind beschränkt, und bewegen sich ausschließlich
durch Depression und Erholung. Valenz ist approach minus avoidance.

**Warum die Erholung zählt.** Depression allein würde jede Synapse innerhalb
eines Korpusdurchlaufs auf null drücken. Die Synapse pendelt sich dort ein, wo
die empfangene Depression die ohnehin laufende Erholung aufwiegt, nämlich bei
`w_baseline − learning_rate × p × d / recovery_rate` für eine Zelle, die einen
Anteil `p` der Zeit aktiv ist bei mittlerem Dopamin `d`. Dieses *Verhältnis*,
nicht eine der beiden Raten allein, legt fest, wie hart sich die Fliege
festlegen darf. Erholung wird pro Präsentation angewendet statt pro Epoche, und
exakt kompoundiert statt linear: ein Batch von tausend Präsentationen bei 0,0015
würde eine Synapse sonst um 150 % des Weges zum Ruhewert bewegen und darüber
hinausschießen.

---

## 5. Dopamin: zwei verschiedene Aufgaben

Dopamin tut hier zwei Dinge, und es sind wirklich nicht dieselben.

**Im Training ist es ein Vorhersagefehler.** Eine Fliege schüttet kein Dopamin
aus, weil etwas Gutes passiert ist, sondern weil etwas *Besseres als erwartet*
passiert ist. Felsenberg und Kollegen zeigten das 2018 direkt an Drosophila:
dieselben DANs, die eine Erinnerung schreiben, revidieren sie auch, wenn die
Vorhersage sich als falsch erweist. Zwei Cluster teilen sich das Vorzeichen. PAM
signalisiert besser-als-erwartet und innerviert die Kompartimente, deren MBONs
Vermeidung treiben; PPL1 signalisiert schlechter-als-erwartet und innerviert die
Approach-Kompartimente. So oder so ist der synaptische Effekt Depression. Diese
Asymmetrie ist das gesamte Valenzsystem der Fliege.

**Beim Zuhören ist es ein Akkumulator.** Ein Perzept ist 800 ms, und die Fliege
soll darauf nicht ihr Leben verwetten. Der Pool integriert Evidenz, und das Tier
legt sich fest, wenn er eine Schwelle überschreitet. Diese Überschreitung ist
das, was die App als Reaktionszeit meldet.

Zwei Details im Akkumulator sind tragend:

- **Die tonische Grundlinie.** Dopaminerge Neuronen feuern permanent, und nur
  die phasische Auslenkung über diesen Hintergrund trägt ein Signal. Ohne die
  Subtraktion füllt sich der Pool nur: ein siebenminütiger Vortrag enthält
  irgendeine Sekunde, die vage nach einem Synth-Stab klingt, nichts läuft je ab,
  und die Fliege begeistert sich irgendwann für alles. Das Einfügen brachte die
  Track-Spezifität von 0,57 auf den Wert in der README.
- **Die sättigende Eingangskennlinie.** Ohne sie ist der Antrieb proportional
  dazu, wie weit die Evidenz über der Grundlinie liegt, und da ein sicheres
  Perzept nur ein Stück darüber liegt, lädt ein Track, bei dem die Fliege sicher
  ist, den Pool mit 40 % der Rate, die vollständige Gewissheit hätte. Die
  nützliche Statistik ist, wie *oft* die Fliege ja sagt, nicht um wie viel, und
  eine sättigende Kennlinie misst genau das. Sie ist außerdem das, was Neuronen
  tun.

Zeitkonstante, Grundlinie und Schwelle werden **nicht gelernt**. Sie sind eine
Entscheidungsregel, gewählt von `training/train.py` auf Out-of-Fold-Spuren, und
drei Zahlen gegen die zurückgehaltenen Tracks zu wählen ist ein milder
Optimismus, den die Track-Zahlen tragen und die Perzept-AUCs nicht.

---

## Was dieses Modell nicht ist

- **Kein Fliegenohr.** Eine Fliege kann keinen Popsong hören. Das Johnston-Organ
  wird hier als Frequenzanalysator benutzt, weil es einer ist, nicht weil eine
  Fliege das je täte.
- **Nicht die Neuronenzahl einer Fliege, außer in der Calyx.** 180 Rezeptoren
  sind keine 480 Sinneszellen, und zwei MBON-Kompartimente sind nicht die etwa
  34, die das Konnektom beschreibt.
- **Kein Online-Lernen.** Eine echte Fliege schreibt eine Erinnerung in einem
  Durchgang. Diese hier braucht 60 Epochen über einen festen Korpus, weil sie
  einen Song über Re-Encodes hinweg erkennen soll und nicht eine einzelne
  Episode erinnern.
- **Keine Aussage darüber, wie irgendetwas Musik hört.** Es ist die Aussage,
  dass ein spärlicher Zufalls-Expander mit reiner Depressions-Plastizität für
  diese Aufgabe reicht, und das ist eine Aussage über die Architektur.

## Die Zahlen lesen

`models/metrics.json` meldet zwei Fragen, die nicht dieselbe Frage sind, und
`frrf-evaluate` zeichnet sie. Was sie bedeuten und welche man wofür glauben
sollte, steht in der README. Ob man das alles bauen sollte, in
[ETHIK.md](ETHIK.md).

<details>
<summary>🇬🇧 English</summary>

Which numbers in `brain/config.py` come from the fly and which are engineering,
stage by stage. The claim is narrow: **this is a model of the Drosophila
mushroom body applied to audio, not a fly.**

**Johnston's organ** is a mel filterbank (48 bands, 40 Hz to 8 kHz) read as
tonotopic channels, three 255 ms sub-frames to a percept. The 12 chroma bins are
*not* a fly structure: they are pitch classes, and they exist because harmony
survives a piano cover where timbre does not. They get their own longer
transform because at the mel window a bin is 21.5 Hz, three semitones in the
bass. Measured effect on held-out renditions: AUC 0.802 → 0.828.

**The antennal lobe** is divisive normalisation after Olsen, Bhandawat & Wilson
(2010), with mel normalising against mel and chroma against chroma because they
are different units. `al_sigma`, `al_suppression` and the per-channel gains are
fitted to music, not to odour.

**The Kenyon cells** are the point of the project: a random sparse expansion,
formally a locality-sensitive hash (Dasgupta, Stevens & Navlakha, *Science*
2017), silenced to a few percent by one giant inhibitory neuron. 4,000 cells
because the connectome counts ~2,000 per hemisphere and a fly has two; 20 claws
because the *ratio* is preserved (11 % against the fly's 12 %) rather than the
count; 5 % sparsity because that is the measured figure, and it only wins once
the population is full. The per-cell firing threshold is the least-evidenced
step and is there because the code is measurably worse without it.

**MBON compartments** hold the memory, and learning is subtraction: dopamine
weakens exactly the synapses that were active. Recovery is what stops depression
flooring every synapse; the ratio of the two rates sets how hard the fly may
commit.

**Dopamine does two jobs.** In training it is a prediction error split across
PAM and PPL1, both acting by depression. While listening it is a leaky
accumulator, and two details carry it: the tonic baseline (without it nothing
ever drains and the fly eventually likes everything; adding it took track
specificity from 0.57) and a saturating input curve (which measures how *often*
the fly says yes rather than by how much). Those three numbers are a decision
rule chosen on out-of-fold traces, not something learned.

**What it is not:** a fly's ear, a fly's neuron count outside the calyx, online
learning, or any claim about how anything hears music. It is a claim about an
architecture.

</details>

> Welche Zahl gehört wem, 2026.
