# Running VibeBite on RunPod + Expo on your phone

This guide assumes you can't run Docker on the Mac and want to push everything
to GitHub, pull on RunPod, and connect your phone's Expo client to RunPod's API.

## 0. Prereqs
- A RunPod pod with Python 3.10+ (3.11 recommended) and a public IP / proxy URL.
- Your GitHub SSH key pasted into RunPod (or use a deploy key).
- Expo Go app on your phone — but **only for the auth/list/voting screens**.
  Anything that needs Expo Notifications or Maps will need a dev build instead
  (out of scope for the current milestone).

---

## 1. Pull on RunPod and bring up the API

```bash
# inside the RunPod pod
git clone git@github.com:atifabedeen/vibePulse.git
cd vibePulse

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e services/api -e services/agents

cp .env.example .env
# Edit .env — set GEMINI_API_KEY (and optionally OPENAI_API_KEY).
# DATABASE_URL can stay as the default SQLite path or switch to Postgres.
```

### 1a. SQLite (zero-install — recommended for first boot)

```bash
cd services/api
alembic upgrade head
python -m app.scripts.seed
cd ..

# bind to 0.0.0.0 so RunPod's proxy can reach it
uvicorn services.api.app.main:app --host 0.0.0.0 --port 8000
```

### 1b. Postgres + pgvector (when you want the production path)

```bash
# RunPod usually has docker available; if so:
docker compose up -d postgres redis
# then in .env:
# DATABASE_URL=postgresql+psycopg://vibebite:vibebite@localhost:5432/vibebite

cd services/api && alembic upgrade head && python -m app.scripts.seed
uvicorn services.api.app.main:app --host 0.0.0.0 --port 8000
```

### 1c. Verify the API

In another shell on the pod:
```bash
curl http://localhost:8000/health         # {"status":"ok"}
curl http://localhost:8000/api/v1/health  # same
```

Note the **public URL** RunPod gives you for port 8000. It looks like
`https://<pod-id>-8000.proxy.runpod.net`.

---

## 2. Run the LangGraph CLI demo (sanity check, no mobile needed)

```bash
# rest assured the API isn't required for this — agents run standalone
python -m vibebite_agents.run_demo
python -m vibebite_agents.run_demo --reject
python -m vibebite_agents.run_demo --reject-twice
```

Each prints the merged group constraints and top-5 ranked restaurants. The
`--reject*` flags exercise the HITL replan loop.

---

## 3. Run the Expo app

You have three options here. Pick whichever fits.

### 3a. Locally on your Mac (preferred — fastest iteration)

You'll need Node 20 LTS:
```bash
brew install node              # if you have admin to install brew packages
# or download directly from nodejs.org
```

Then:
```bash
cd apps/mobile
npm install
# Edit app.json -> expo.extra.apiBaseUrl to your RunPod public URL:
#   "apiBaseUrl": "https://<pod-id>-8000.proxy.runpod.net/api/v1"
npx expo start
```

Scan the QR code with Expo Go on your phone. The phone hits RunPod for API
calls; the JS bundle comes from your Mac over LAN.

### 3b. Expo on RunPod itself

Doable but slow because the JS bundle is served over RunPod's proxy. Same
steps as 3a but run on the pod. Expose port 8081 (Metro bundler) and 19000
(Expo dev server) from RunPod.

### 3c. Build a standalone artifact via EAS

```bash
cd apps/mobile
npm install -g eas-cli
eas login
eas build --profile development --platform ios
```

Takes ~15 minutes; gives you a `.ipa` you sideload via TestFlight. Required
once you add Maps SDK or Notifications.

---

## 4. The end-to-end flow

1. Open the Expo app on your phone.
2. **Register** with any email (`smoke@example.com` works).
3. **Create a mission** — title, description, default Atlanta location, 3km
   radius.
4. Open the mission, go to **Preferences** tab, fill in budget / cuisines /
   dietary / vibe / noise. Hit "Parse with AI" to let Gemini augment from a
   raw comment.
5. Hit **Recommend!** on the overview tab. Spinner shows while the graph
   runs (~1-3s with stubs, ~5-10s with real Gemini).
6. The app polls `/agents/runs` and routes you to the **Runs** tab when the
   graph hits the HITL gate. You see the proposed winner.
7. **Approve** -> done; the Rankings tab now shows the top 5 with LLM-
   generated pros/cons. **Reject** -> bottom-sheet asks for a reason and
   optional budget override; the graph replans and shows a new winner.
8. The **Vote** tab lets each member up/veto specific places.

---

## 5. Inviting friends

1. On a mission's overview, hit "Generate invite link".
2. Copy the deep link (currently a token; in M-Mobile-4 we'll switch to a
   `vibebite://` deep link).
3. Friend installs Expo Go, registers their own account in your build, taps
   the link or pastes the token in the redeem screen (TODO: redeem screen
   not yet built — they can use curl for now).

---

## 6. Common issues

- **API returns 401 from the app**: token expired and refresh failed. Log
  out + log back in.
- **Recommend hangs forever**: check the API logs for `LLMError`. Usually
  a Gemini quota hit. The graph silently degrades to stub but the mobile
  client may show the spinner until /agents/runs status updates — give it
  10-15 seconds.
- **iOS device can't reach localhost**: that's expected. The `apiBaseUrl`
  in `app.json` MUST be the RunPod public URL or your Mac's LAN IP, not
  `localhost` or `127.0.0.1`.
- **`alembic upgrade` fails on Postgres with "extension vector does not
  exist"**: you're on plain Postgres without pgvector. Use the
  `pgvector/pgvector:pg16` image (in `docker-compose.yml`) or `apt install
  postgresql-16-pgvector` on the host.

---

## 7. What's in the repo

| Path | What |
|---|---|
| `services/api/` | FastAPI backend with all 28 endpoints |
| `services/agents/` | LangGraph workflows (parse / search / score / explain / select / replan + HITL) |
| `apps/mobile/` | Expo React Native + TypeScript app |
| `docker-compose.yml` | Postgres + Redis (for option 1b) |
| `implementation.md` | Full spec |
| `.env.example` | Every env var the system reads |

Each milestone has a top-level commit on `main` so `git log` shows the
build progression: `C1+C2`, `C3`, `C4`, `C5`, `C6`.
