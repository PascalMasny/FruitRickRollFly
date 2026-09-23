# web

> Das Frontend.

**TL;DR** · React 19, Vite, TypeScript, keine State-Library. `npm run build`
legt `dist/` ab, und die FastAPI-App liefert das selbst aus, also gibt es einen
Origin und einen Prozess. Die Optik ist ein Grauton-Fenster von 1995, und die
beiden 3D-Panels behalten einen schwarzen Schacht.

```bash
npm install
npm run dev      # Dev-Server auf :5173, proxied die API
npm run build    # schreibt dist/, das die FastAPI-App ausliefert
npm run lint
```

`uvicorn api.main:app` liefert `dist/` vom selben Origin wie die API, ein
gebautes Frontend braucht also kein CORS und keinen zweiten Prozess. Der
Dev-Server auf :5173 ist der einzige Grund, warum `api/main.py` überhaupt eine
CORS-Liste trägt.

## Was die Teile tun

| | |
|---|---|
| `components/UrlInput` | Link einwerfen: YouTube, TikTok oder Instagram |
| `components/StageStrip` | der Signalweg, Stufe für Stufe beleuchtet während er läuft |
| `components/VideoPreview` | der Player, aus unserer eigenen Kopie statt aus einem Embed |
| `components/BrainView` | die Kenyon-Population: welche der 4.000 gerade feuern |
| `components/FlyView` | das Tier selbst, vor dem Monitor, in einem Raum von 1995 |
| `components/Timeline` | Konfidenz und Dopamin-Pool gegen den Abspielkopf |
| `components/Stats` | das Urteil, die Reaktionszeit, die eigenen Zahlen des Modells |
| `components/CorrectionBar` | über den Streifen ziehen und sagen, wo der Song wirklich ist |
| `views/TrainingData` | der Korpus, sortier- und filterbar |
| `views/Workshop` | welche Fliege antwortet, und die Trainingsbefehle |
| `views/Notes` | eine Seite zum Draufschreiben, gespeichert nach `data/notes.md` |
| `lib/useAnalysis` | hängt sich an den Server-Sent-Event-Stream |
| `lib/usePlayhead` | hält die Zeitleiste im Takt mit der Wiedergabe |

Die API streamt den Fortschritt über SSE statt über ein Websocket: der Verkehr
geht in eine Richtung, und ein sich selbst wiederverbindendes `EventSource` ist
auf beiden Seiten weniger Code als ein Socket-Protokoll.

Werkstatt und Notizen werden nur gezeichnet, wenn `/api/health` sagt, dass es
sie gibt. Auf einem öffentlichen Server sind die Routen nicht registriert, und
ein Tab der 404 liefert ist schlimmer als kein Tab.

## Stack

`React 19` · `TypeScript` · `Vite` · `three.js` · `oxlint`

<details>
<summary>🇬🇧 English</summary>

React 19, Vite, TypeScript, no state library. `npm run build` emits `dist/`,
which the FastAPI app serves from the same origin, so a built frontend needs
neither CORS nor a second process; the :5173 dev server is the only reason
`api/main.py` carries a CORS allowlist at all. Progress arrives over SSE rather
than a websocket because the traffic is one-directional and a reconnecting
`EventSource` is less code on both ends. The workshop and notes tabs are drawn
only when `/api/health` says those routes exist. The skin is a grey 1995
application window; the two 3D panels keep a black well, because that is the
only background the Kenyon cells read against.

</details>

> Ein Fenster von 1995 für ein Tier von 1987, 2026.
