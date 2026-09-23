# Ethik

> Ob man das überhaupt darf.

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

## Ich bin kein Ethiker

Am Ende des Tages: ich bin kein Philosoph. Keine Ethikkommission, kein Theologe,
kein spiritueller oder psychologischer Experte. Ich bin jemand, der Software
baut und sich für Gehirne interessiert.

Ich finde es schlicht komisch, dass ich einer Fliege einen Rickroll beibringen
kann. Ich mag den Song. Ich mag es, gerickrollt zu werden, und ich mag es, andere
zu rickrollen, auch 2026 noch. Und ich finde es komisch, dass gerade alles ein
Fliegengehirn ist.

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

**And I am not an ethicist.** Not a philosopher, not an ethics committee, not a
theologian. I build software and find brains interesting. I think it is funny
that I can train a fly on a Rickroll. I like the song, I like being rickrolled,
I like rickrolling people, still, in 2026. And I find it funny that everything
is a fly brain right now. That is the honest reason this exists. Everything
above is an attempt to take that answer seriously after the fact, which is the
wrong order, and I wrote it down anyway because the questions turned up while I
was building and a joke that cannot survive them is not a good joke.

</details>

> Ein Witz, der die Fragen aushalten muss, die er auslöst, 2026.
