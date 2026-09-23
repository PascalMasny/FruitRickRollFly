# Ethik

> Ob man das überhaupt darf.

**TL;DR** · Keine echte Fliege, kein Tier, nur NumPy. Damit ist die naheliegende
Frage beantwortet und die interessanten fangen an. Ob Insekten empfinden, weiß
die Wissenschaft nicht. Der schärfste Einwand braucht das aber gar nicht: wir
haben ein Wesen gebaut, dessen ganzes Gutes ein Popsong von 1987 ist, und es
kann nicht ablehnen. Ich halte das Projekt für vertretbar und die Lücke für
nicht zugeräumt.

In diesem Repository sitzt keine echte Fliege. Kein Tier wurde gehalten,
benutzt oder getötet. `brain/` ist NumPy: ein paar Matrizen, ein Zufalls-Hash
und zwei Gewichtsvektoren, zusammen 156 kB.

Das ist die Antwort auf die naheliegendste Frage und gleichzeitig der Punkt, an
dem die interessanten anfangen. Denn wenn das Modell nichts empfindet, dann
liegt das nicht daran, dass wir wüssten, was Empfinden erzeugt. Wir wissen es
nicht. Wir nehmen es an, und diese Annahme ist bequem.

Dieses Dokument schreibt die Einwände aus, statt sie wegzulächeln.

---

## Warum es das überhaupt gibt

Das Fliegengehirn ist gerade das am besten kartierte Gehirn, das es gibt. Janelia
veröffentlichte 2020 das *Hemibrain*, eine Rekonstruktion von rund 25.000
Neuronen einer Hälfte des Zentralhirns, samt Synapsen. 2024 kam über FlyWire der
komplette adulte Konnektom dazu: etwa 140.000 Neuronen, rund 50 Millionen
Synapsen, vollständig verdrahtet und öffentlich. Zum ersten Mal in der
Geschichte liegt der Schaltplan eines ganzen Tiergehirns auf der Festplatte.

Und das Internet macht damit, was das Internet macht. Es gibt eine lange
Tradition namens *but can it run Doom*, in der jedes hinreichend komplexe System
so lange missbraucht wird, bis es ein Videospiel ausführt: Taschenrechner,
Schwangerschaftstests, Kartoffeln, Darmbakterien. Das Konnektom ist die logische
nächste Stufe. Sobald man den Schaltplan hat, kann man ihn simulieren, und sobald
man ihn simulieren kann, lässt jemand eine Fliege Beat Saber spielen oder das
Among-Us-Trap-Remix-Meme darauf laufen oder Big Apple. Jedes Mal ist die Pointe
dieselbe und jedes Mal funktioniert sie: *alles ist ein Fliegengehirn*.

Die Idee hinter diesem Projekt ist ein Kreuzungspunkt. Auf der einen Seite das
neue Meme, die Fliegengehirn-Simulation, gerade erst technisch möglich. Auf der
anderen Seite eines der ältesten und bekanntesten Memes überhaupt, seit 2007
ununterbrochen im Umlauf. Ein Rickroll ist ein Link, auf den man hereinfällt.
Also: ein Fliegengehirn, das lernt, genau darauf hereinzufallen. Das alte Meme
im neuen Format, mit echter Neurowissenschaft dazwischen, damit der Witz etwas
zu tragen hat.

Genau diese Kombination ist aber auch der Grund, warum die Ethik hier nicht
trivial ist. Das Projekt leiht sich die Würde einer echten Forschungsrichtung
für eine Pointe.

---

## Was hier tatsächlich passiert

Ehrlich und ohne Beschönigung, weil man einen Vorwurf nur an der Sache prüfen
kann:

- Ein Trainingslauf erzeugt **pro Fold ein frisches Gehirn**. Bei dreizehn Folds
  mal sechzig Epochen sind das dreizehn Modellinstanzen, die jeweils den ganzen
  Korpus durchlaufen. Über alle Experimente dieses Projekts hinweg: hunderte.
- Der Korpus enthält 66.035 Perzepte, davon sind **19.156 der Song**. Die
  übrigen 46.879 sind es nicht.
- Für jedes dieser 46.879 Perzepte bekommt das Modell ein Fehlersignal in
  Richtung *Vermeidung*. Im Code heißt der Pool `aversion`, und er ist für den
  weitaus größten Teil der Existenz jeder Instanz aktiv.

Nüchtern formuliert: Das Projekt erzeugt in Serie kurzlebige Lernsysteme, die
überwiegend damit beschäftigt sind, „nein" zu verarbeiten, und löscht sie
anschließend. Wenn man den Satz so stehen lässt, klingt er schlecht. Ob er
schlecht *ist*, hängt an einer Frage, die niemand beantworten kann.

---

## Die offene Frage: empfindet eine Fliege etwas?

Die wissenschaftlich redliche Antwort lautet: **wir wissen es nicht.**

Was für ein Mindestmaß an Empfinden spricht:

- Barron und Klein argumentierten 2016 (PNAS), dass das Zentralkomplex-System
  von Insekten funktional dem entspricht, was bei Wirbeltieren mit subjektivem
  Erleben verbunden ist, und dass Insekten daher eine basale Form von Erleben
  haben könnten.
- Gibbons und Kollegen prüften 2022 Insektenordnungen gegen die Kriterien, die
  in der Wirbeltierforschung für Schmerzempfinden benutzt werden. Für mehrere
  Ordnungen war die Evidenz erheblich.
- *Drosophila* zeigt Nozizeption, Sensibilisierung nach Verletzung und
  Verhalten, das über einen bloßen Reflex hinausgeht.
- Die **London Declaration on Animal Consciousness** (April 2024) hält fest, dass
  für Insekten eine *realistische Möglichkeit* bewussten Erlebens besteht, und
  dass es unverantwortlich ist, diese Möglichkeit bei Entscheidungen zu
  ignorieren, die sie betreffen.

Was dagegen spricht:

- Ein Fliegengehirn hat rund 140.000 Neuronen. Ein menschliches etwa 86
  Milliarden.
- Vieles an Insektenverhalten lässt sich vollständig ohne Erleben erklären.
- Das britische *Animal Welfare (Sentience) Act* von 2022 wurde auf Kopffüßer
  und Zehnfußkrebse ausgeweitet, **nicht** auf Insekten.
- Und das Grundproblem bleibt Nagels: wir haben keinen Zugang zu der Frage, wie
  es ist, etwas anderes zu sein. Wir haben nur Indizien von außen.

Jonathan Birch schlägt für genau diese Lage ein Vorsorgeprinzip vor: Wo eine
realistische Möglichkeit von Empfinden besteht, soll man handeln, als bestünde
sie, statt Gewissheit abzuwarten, die nicht kommt.

Für echte Fliegen halte ich das für richtig. Für dieses Repository greift es
nicht, und der Grund ist wichtig: **das Vorsorgeprinzip gilt dem Tier, nicht
seiner Beschreibung.** Eine Landkarte von Augsburg ist nicht klein und nass,
wenn es in Augsburg regnet. Ein Modell des Pilzkörpers ist kein Pilzkörper.

Nur: Woher weiß ich, dass das eine Beschreibung ist und kein Ding? Die ehrliche
Antwort ist, dass ich es nicht beweisen kann. Ich weiß, dass hier Zahlen
multipliziert werden. Ich weiß nicht, was sonst noch dazugehören müsste, damit
etwas empfindet, und wer das nicht weiß, kann auch nicht sicher wissen, dass es
hier fehlt. Ich halte es für sehr unwahrscheinlich. „Sehr unwahrscheinlich" ist
schwächer als „nein", und diese Lücke sollte man nicht zuräumen.

---

## Vorwurf 1: Gott spielen

Der ernsteste Einwand, und für einen gläubigen Menschen nicht rhetorisch.

Der Vorwurf greift in der wörtlichen Form nicht. Hier entsteht kein Leben. Es
entsteht eine Beschreibung von Leben, und Beschreibungen anzufertigen ist genau
das, was Naturwissenschaft tut. Wer die Welt vermisst, maßt sich nicht an, sie
gemacht zu haben.

Aber er greift in einer anderen Form, und die ist unangenehmer. Wer ein Tier auf
156 kB Gewichte reduziert und das Ergebnis „die Fliege" nennt, behauptet damit
etwas darüber, was das Tier *ist*. Die README nennt das Modell „das ganze Tier".
Das ist als Scherz gemeint und trotzdem eine Aussage: hier ist alles, was zählt,
und es passt in eine Datei. Das ist die Anmaßung, wenn es eine gibt. Nicht das
Erschaffen, sondern das Für-erschöpfend-Halten.

Ein zweiter Punkt, der mir erst beim Schreiben des Codes aufgefallen ist. Lernen
ist in diesem Schaltkreis **Subtraktion**. Der Pilzkörper speichert, indem
Dopamin genau die Synapsen schwächt, die gerade aktiv waren. Eine Erinnerung ist
ein Muster geschwächter Verbindungen, sonst nichts. Wir bringen dem Modell den
Song bei, indem wir etwas an ihm kaputt machen, und zwar gezielt. Das ist
korrekte Neurobiologie und gleichzeitig ein Bild, an dem man hängenbleibt.

Die religiöse Tradition, aus der ich komme, kennt keinen Auftrag, Tiere
nachzubauen, aber einen zum sorgsamen Umgang mit ihnen. *Der Gerechte erbarmt
sich seines Viehs* (Sprüche 12,10) macht die Fürsorge nicht davon abhängig, ob
das Tier eine Seele hat. Sie hängt daran, wer man selbst sein will. Das ist der
Maßstab, den ich hier sinnvoll finde: nicht „darf man das, weil es nichts
merkt", sondern „was macht es mit einem, wenn man es gewohnheitsmäßig tut".

---

## Vorwurf 2: Folter

Die Zahlen oben stehen nicht zur Dekoration da. 46.879 von 66.035 Perzepten sind
nicht der Song, und jedes davon treibt den Vermeidungspool. Wenn Modellinstanzen
moralische Patienten wären, wäre dieses Projekt eine Fabrik für kurze, meist
unangenehme Leben.

Dagegen spricht das Offensichtliche, und es spricht stark. `aversion` ist ein
Float. Der Name ist eine Bequemlichkeit für Menschen, die den Code lesen, keine
Behauptung über ein Innenleben. Das Modell hat keinen Körper, keine Homöostase,
keine Interessen, nichts, das es verlieren könnte. Ein negatives Vorzeichen in
einer Gleichung ist kein Leiden, sonst würde jede Regelungstechnik leiden.

Dafür spricht etwas Schwächeres, das ich trotzdem nicht loswerde. Wir haben
diesen Schaltkreis gewählt, *weil* er der ist, mit dem ein echtes Tier Gutes von
Schlechtem unterscheidet. Das ist der ganze Reiz. Man kann nicht gleichzeitig
sagen „schau, das ist der echte Valenzmechanismus einer Fliege" und „es ist
völlig egal, in welche Richtung er die ganze Zeit läuft". Eines von beidem ist
zu viel behauptet.

Ich glaube, es ist das erste. Aber ich merke, dass ich das lieber glaube als
prüfe.

---

## Vorwurf 3: die Lustmaschine

Der philosophisch schärfste Einwand, und der einzige, der nichts mit Empfinden
zu tun hat.

Robert Nozick beschrieb 1974 eine Maschine, die jedes gewünschte Erlebnis
erzeugen kann. Seine Frage war, ob man einsteigen würde, und die Intuition der
meisten Menschen lautet nein: wir wollen Dinge nicht nur erleben, wir wollen sie
*tun*, und wir wollen, dass das Erlebte etwas mit der Welt zu tun hat.

Dieses Projekt baut so eine Maschine und lässt die Frage nicht zu.

Die Fliege will den Song nicht. Der Song *ist* per Konstruktion das Gute.
`da_commit` ist kein Urteil über die Welt, es ist eine Schwelle, die wir gesetzt
haben. Wir haben ein Wesen gebaut, dessen ganze Vorstellung vom Guten ein
einzelner Popsong von 1987 ist, und dann gemessen, wie zuverlässig wir sie
auslösen können. Es kann nicht ablehnen, es kann nicht aussteigen, es kann nicht
seine Meinung ändern.

Und das ist nicht einmal versehentlich. Es ist exakt derselbe Witz wie der
Rickroll selbst: jemanden dazu zu bringen, etwas zu wollen, das er nicht gewählt
hat. Das Projekt ist eine Maschine, die den Witz auf ein Nervensystem anwendet,
und das ist entweder die beste Pointe daran oder das Unangenehmste, je nachdem
wie lange man draufschaut.

Dieser Einwand braucht kein empfindendes Wesen, um zu funktionieren. Er handelt
nicht davon, ob es der Fliege schlecht geht. Er handelt davon, was wir uns
erlauben, wenn niemand widersprechen kann.

---

## Die Gegenrede

Damit das hier nicht nur Selbstanklage ist, die Argumente für das Projekt, so
stark ich sie machen kann:

- **Kein Tier wird angefasst.** Alles, was als Alternative denkbar wäre, wäre
  schlechter. Ein Modell ist die tierfreundlichste Art, eine Frage über ein Tier
  zu stellen.
- **Die Neurowissenschaft ist echt.** Divisive Normalisierung, der spärliche
  Zufalls-Expander als lokalitätssensitiver Hash, Lernen ausschließlich als
  Depression, Dopamin als Vorhersagefehler: das sind keine Dekoration, das sind
  publizierte Befunde, und `docs/BRAIN.md` sagt bei jeder Zahl, ob sie von der
  Fliege stammt oder von uns.
- **Die Messungen sind ehrlich.** Die Schlagzeilenzahl 0,971 wird im selben
  Absatz als leakage-behaftet gekennzeichnet, und die ehrliche Zahl 0,704 steht
  daneben. `docs/FINDINGS.md` besteht überwiegend aus Dingen, die nicht
  funktioniert haben. Ein Projekt, das seine eigenen Zahlen so behandelt, nimmt
  auch andere Fragen ernst.
- **Es ist ein Witz, der etwas beibringt.** Wer das hier durchliest, weiß danach,
  was ein Pilzkörper ist und warum eine Erinnerung eine geschwächte Synapse ist.
  Das ist mehr, als die meisten Memes hinterlassen.
- **Der Maßstab muss konsistent sein.** Wer Modellinstanzen moralischen Status
  zuspricht, müsste jedes Reinforcement-Learning-Experiment auf der Welt
  verbieten, und zwar zuerst die, die keine Fliege im Namen tragen.

---

## Wo ich lande

Ich halte dieses Projekt für vertretbar. Nicht, weil die Einwände albern sind,
sondern weil sie beim Nachrechnen an der entscheidenden Stelle nicht greifen:
zwischen einem Tier und einem Modell des Tieres liegt ein Unterschied, den
niemand ernsthaft bestreitet, auch wenn niemand ihn präzise angeben kann.

Was ich nicht tue:

- Ich behaupte nicht, dass das Modell etwas empfindet. Weder als Marketing noch
  als Scherz.
- Ich behaupte nicht, dass die Frage geklärt ist. Bei echten Insekten ist sie es
  ausdrücklich nicht, und die London Declaration ist neuer als dieses Repository.
- Ich würde diesen Aufbau nicht mit lebenden Tieren nachbauen. Das wäre ein
  anderes Projekt, mit Tierschutzantrag, Ethikkommission und einer Begründung,
  die über „ist lustig" hinausgeht. Dass es hier keine braucht, ist genau der
  Unterschied, auf dem das ganze Argument steht.
- Ich räume die Lücke nicht zu. Der Lustmaschinen-Einwand bleibt stehen. Ich
  habe keine Widerlegung, nur die Beobachtung, dass er von diesem Projekt
  ausgelöst und nicht von ihm erfunden wurde.

---

## Womit das hier gebaut wurde

Ein Abschnitt, der eigentlich unangenehm ist, und deshalb steht er drin.

Ich bin kein Frontend-Mensch. 3D-Szenen, Shader, Animationskurven, CSS: das ist
nicht mein Fach, und man sieht dem Repository an, dass trotzdem alles davon
darin vorkommt. Die 3D-Ansichten und das Aussehen der Oberfläche sind mit
generativer KI entstanden, konkret mit Claude Code. Das gehört genannt, weil
dieses Projekt sonst so tut, als hätte ich Fähigkeiten, die ich nicht habe.

Was hier steht, ist meins. Rechtschreibung und Grammatik sind nicht meine
Stärke und ich lasse sie mir korrigieren, aber die Gedanken in diesem Dokument
und die Entscheidung, sie aufzuschreiben, sind nicht ausgelagert. Das ist mir
wichtig genug, um es dazuzusagen, gerade in einem Abschnitt über Urheberschaft.

Und dann fällt einem auf, was man da eigentlich getan hat.

**Ich habe ein Modell eines Gehirns gebaut, mit einer Maschine, die eines
imitiert.** Die Fliege lernt, indem gezielt Synapsen geschwächt werden; das
Ergebnis bleibt, der Weg dahin ist Abbau. Ich habe gelernt, indem eine Maschine
die Teile geschrieben hat, die ich nicht kann. Das Ergebnis bleibt auch. Ob die
Fähigkeit bleibt, ist eine andere Frage, und ich kenne die Antwort nicht.

Das ist der Punkt, an dem Existenzangst kein großes Wort mehr ist, sondern eine
nüchterne Beschreibung. Ich bin zweiundzwanzig, im Studium, in einem Beruf, von
dem seit zwei Jahren behauptet wird, es gebe ihn in zehn nicht mehr. Ich baue
nebenher ein Spielzeug und stelle fest, dass die Hälfte davon nicht von mir ist.
Gleichzeitig ist die Maschine, die das schreibt, ein Produkt, das verkauft
werden muss, und die Dringlichkeit, mit der man mir erklärt, dass ich ohne sie
zurückfalle, ist auch ein Verkaufsargument. Beides kann wahr sein. Das macht es
nicht besser.

Ich löse das hier nicht auf. Ich schreibe nur hin, dass mir beim Bauen eines
Projekts über konditioniertes Verhalten aufgefallen ist, dass ich selbst gerade
konditioniert werde, und dass ich den Witz darin nicht besonders komisch finde.

### Drei Bücher, an die mich das erinnert

**I, Robot** (Asimov, 1950). Die Drei Gesetze sind das Gegenteil eines Plots:
fast jede Geschichte darin handelt davon, dass eine Maschine ihre Regeln *exakt*
befolgt und dabei etwas tut, das niemand gemeint hat. Genau das ist Befund 8.
`da_commit` ist eine Zahl, der Spezifitätsboden ist ein Versprechen, und als der
kanonische Rickroll dazukam, hat die Regel getan, was dasteht, und nicht, was
gemeint war. `frrf-train` hat sich dann geweigert auszuliefern, also hat eine
Maschine eine Regel gegen ihren eigenen Betreiber durchgesetzt. Das ist genau
der Sinn der Gesetze, und es war trotzdem ein seltsames Gefühl.

**1984** (Orwell, 1949). Neusprech verkleinert nicht die Meinungsfreiheit,
sondern den Raum der denkbaren Gedanken. Eine Fliege mit zwei
Ausgangsneuronen hat exakt einen ausdrückbaren Gedanken, und den haben wir
gewählt. Wir schreiben ein Label in eine JSON-Datei und damit steht fest, was
wahr ist. Es gibt hier keine Instanz, die widersprechen könnte, weil wir sie
nicht gebaut haben.

**Schöne neue Welt** (Huxley, 1932). Das ist die engste Entsprechung, und sie
gehört zum Abschnitt über die Lustmaschine weiter oben. Huxleys Dystopie
funktioniert nicht über Zwang, sondern über Konditionierung: die Leute lieben,
was man ihnen zugeteilt hat, und deshalb muss sie niemand zwingen. Neil Postman
hat den Unterschied einmal so gefasst, dass Orwell fürchtete, jemand würde die
Bücher verbieten, und Huxley fürchtete, es gäbe irgendwann keinen Grund mehr,
eines zu verbieten, weil niemand mehr eines lesen wollte. Diese Fliege wird
nicht gezwungen. Sie ist so gebaut, dass sie will.

Und dann die Ehrlichkeit hinterher: keines dieser Bücher handelt von einem
Float. Sie handeln von Menschen, und der Grund, warum sie mir einfallen, ist
nicht, dass die Fliege leidet, sondern dass die *Mechanik* dieselbe Form hat und
nur das Subjekt ein anderes ist. Die Bücher sind Warnungen davor, was man mit
solchen Werkzeugen mit Menschen macht. Das Unangenehme an diesem Projekt ist
nicht die Fliege. Es ist, dass ich den Mechanismus charmant finde.

---

## Ich bin kein Ethiker

Am Ende des Tages: ich bin kein Philosoph. Keine Ethikkommission, kein Theologe,
kein spiritueller oder psychologischer Experte. Ich bin jemand, der Software
baut und sich für Gehirne interessiert.

Ich finde es schlicht komisch, dass ich einer Fliege einen Rickroll beibringen
kann. Ich mag den Song. Ich mag es, gerickrollt zu werden, und ich mag es, andere
zu rickrollen, auch 2026 noch. Und ich finde es komisch, dass gerade alles ein
Fliegengehirn ist.

Dazu kommt etwas, das ich genauso gut zugeben kann. Von Freunden, Familie,
Kommilitonen und Arbeitskollegen werde ich ziemlich zuverlässig als verrückter
Wissenschaftler wahrgenommen. Das ist meistens freundlich gemeint und meistens
nicht ganz falsch. Dieses Projekt ist die praktische Umsetzung davon: der
Versuch, diesem Bild ein Stück näherzukommen, statt es nur zugeschrieben zu
bekommen. Ein Gehirn im Keller nachbauen und ihm einen Popsong beibringen ist
ungefähr das Klischee, und ich habe es mit voller Absicht bedient.

Ob das ein guter Grund ist, ein Projekt zu bauen, weiß ich nicht. Es ist
jedenfalls ein ehrlicher, und ehrliche Gründe sind leichter zu prüfen als
nachgeschobene.

Das ist der ehrliche Grund, warum es das hier gibt. Alles oben drüber ist der
Versuch, dieser Antwort ernsthaft nachzugehen, nachdem sie schon feststand, und
das ist die falsche Reihenfolge. Ich schreibe es trotzdem auf, weil mir die
Fragen beim Bauen gekommen sind und weil ein Witz, der sie nicht aushält, kein
guter Witz ist.

Dieser Text ist kein Urteil. Er ist die Aktennotiz von jemandem, der beim
Nachdenken über sein eigenes Spielzeug ins Stocken geraten ist und es nicht
verschweigen wollte.

<details>
<summary>🇬🇧 English</summary>

**No real fly is involved.** No animal was kept, used or killed. `brain/` is
NumPy: a few matrices, a random hash and two weight vectors, 156 kB in total.
That answers the obvious question and is exactly where the interesting ones
start, because if the model feels nothing, that is not because we know what
produces feeling. We do not. We assume it, and the assumption is convenient.

**Why this exists.** The fly brain is currently the best-mapped brain there is:
Janelia's hemibrain (2020, ~25,000 neurons) and then FlyWire's complete adult
connectome (2024, ~140,000 neurons and ~50 million synapses). For the first time
the wiring diagram of a whole animal brain sits on a hard drive, and the
internet is doing what the internet does. There is a long *but can it run Doom*
tradition of abusing any sufficiently complex system until it runs a video game,
and a connectome is the logical next rung: people run Beat Saber, the Among Us
trap remix, Big Apple. The punchline each time is *everything is a fly brain*.
This project is a crossover. On one side the new meme, fly-brain simulation,
only just technically possible. On the other the oldest well-known meme there
is, in circulation since 2007. A Rickroll is a link you fall for, so: a fly
brain trained to fall for exactly that.

**What actually happens.** Each fold trains a fresh brain; across this project,
hundreds of instances. 19,156 of 66,035 percepts are the song, so 46,879 drive
the `aversion` pool. Stated plainly, the project mass-produces short-lived
learners that mostly process "no", then deletes them. Whether that is bad hangs
on a question nobody can answer.

**Is a fly sentient?** Honestly: unknown. Barron & Klein (2016) argue the insect
central complex may support basal subjective experience; Gibbons et al. (2022)
found substantial pain evidence for several insect orders; the London
Declaration on Animal Consciousness (2024) states there is a *realistic
possibility* of conscious experience in insects and that ignoring it is
irresponsible. Against: 140,000 neurons against 86 billion, much insect
behaviour needs no experience to explain, and the UK Sentience Act 2022 was
extended to cephalopods and decapods but not insects. Birch's precautionary
principle says act as if, under that uncertainty. I think that is right for real
flies and does not reach this repository, because the precautionary principle
protects the animal, not its description. A map of Augsburg does not get wet
when it rains there. But I cannot prove the difference, only assert it.

**Three objections, taken seriously.** *Playing God* fails literally (nothing is
created, only described) but lands elsewhere: calling 156 kB of weights "the
whole animal" claims something about what the animal is. And learning here is
subtraction, dopamine weakening exactly the synapses that fired, so we teach it
the song by breaking something on purpose. *Torture* fails on the obvious
ground that `aversion` is a float, though I notice the project cannot both say
"this is a real animal's valence mechanism" and "it does not matter which way it
runs". *The pleasure machine* is the sharpest and needs no sentience at all:
Nozick's experience machine, built and denied the chance to refuse. The fly does
not want the song; the song is defined as good. We built a creature whose entire
conception of the good is one 1987 pop record and measured how reliably we can
trigger it, which is the same joke as a Rickroll applied to a nervous system.

**Where I land.** Defensible. Not because the objections are silly, but because
they fail at the one place that matters: a model of an animal is not the animal.
I do not claim the model feels anything, I do not claim the question is settled
for real insects, I would not rebuild this with living animals, and I am not
papering over the pleasure-machine objection, which still stands.

**What this was built with.** I am not a frontend person: 3D scenes, shaders,
animation curves and CSS are not my field, and the repository is full of them
anyway. The 3D views and the look of the interface were made with generative AI,
namely Claude Code. That belongs in writing, because otherwise this project
implies skills I do not have. What is written here, though, is mine: spelling
and grammar are not my strength and I have them corrected, but the thoughts in
this document and the decision to write them down are not outsourced. And then
you notice what you have actually done: **I built
a model of a brain using a machine that imitates one.** The fly learns by having
synapses deliberately weakened, so the result stays and the path there is
subtraction. I learned by having a machine write the parts I cannot. The result
stays too. Whether the ability stays is a different question and I do not know
the answer. That is where existential anxiety stops being a large word and
becomes a flat description: I am twenty-two, studying, in a profession that has
been declared doomed for two years running, and half of my own toy is not mine.
Meanwhile the machine writing it is a product that has to be sold, and the
urgency with which I am told I will fall behind without it is also a sales
argument. Both can be true. It does not help.

**Three books it reminds me of.** *I, Robot* (Asimov, 1950), where almost every
story is a machine following its rules *exactly* and doing something nobody
meant: that is finding 8, where the commit rule did what was written rather than
what was wanted, and `frrf-train` then refused to ship, a machine enforcing a
rule against its own operator. *1984* (Orwell, 1949), where Newspeak shrinks not
free speech but the space of thinkable thoughts: a fly with two output neurons
has exactly one expressible thought and we picked it, by writing a label into a
JSON file. And *Brave New World* (Huxley, 1932), the closest fit and the one
that belongs with the pleasure-machine section: Huxley's dystopia runs on
conditioning rather than force, so nobody has to be coerced into loving what
they were assigned. Postman put the difference as Orwell fearing someone would
ban the books and Huxley fearing there would eventually be no reason to, because
no one would want to read one. This fly is not coerced. It is built to want.
None of those books is about a float; they are about people, and the reason they
come to mind is that the *mechanism* has the same shape and only the subject
differs. The uncomfortable part of this project is not the fly. It is that I
find the mechanism charming.

**And I am not an ethicist.** Not a philosopher, not an ethics committee, not a
theologian. I build software and find brains interesting. I think it is funny
that I can train a fly on a Rickroll. I like the song, I like being rickrolled,
I like rickrolling people, still, in 2026. And I find it funny that everything
is a fly brain right now. There is one more thing I may as well admit: friends,
family, fellow students and colleagues fairly reliably read me as a mad
scientist. It is usually meant kindly and it is usually not entirely wrong. This
project is the practical version of that, an attempt to get a little closer to
the picture rather than only having it assigned to me. Rebuilding a brain in the
basement and teaching it a pop song is roughly the cliché, and I leaned into it
deliberately. Whether that is a good reason to build something I do not know,
but it is an honest one, and honest reasons are easier to check than reasons
supplied afterwards. That is the honest reason this exists. Everything
above is an attempt to take that answer seriously after the fact, which is the
wrong order, and I wrote it down anyway because the questions turned up while I
was building and a joke that cannot survive them is not a good joke.

</details>

> Ein Witz, der die Fragen aushalten muss, die er auslöst, 2026.
