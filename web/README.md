# web

The frontend: React 19, Vite, TypeScript, no state library.

```bash
npm install
npm run dev      # dev server on :5173, proxying the API
npm run build    # emits dist/, which the FastAPI app serves itself
npm run lint
```

`uvicorn api.main:app` serves `dist/` from the same origin as the API, so a
built frontend needs no CORS and no second process. The dev server on :5173 is
the only reason `api/main.py` carries a CORS allowlist at all.

## What the pieces do

| | |
|---|---|
| `components/UrlInput` | paste a YouTube link |
| `components/VideoPreview` | the thumbnail, while the audio downloads |
| `components/StageStrip` | the signal path, lit up stage by stage as it runs |
| `components/BrainView` | the Kenyon cell population — which of the 4,000 are firing |
| `components/Timeline` | confidence and the dopamine pool against the playhead |
| `components/Stats` | the verdict, the reaction time, the model's own numbers |
| `lib/useAnalysis` | subscribes to the server-sent event stream |
| `lib/usePlayhead` | keeps the timeline in step with playback |

The API streams progress over SSE rather than a websocket: the traffic is
one-directional and a reconnecting `EventSource` is less code on both ends than
a socket protocol.
