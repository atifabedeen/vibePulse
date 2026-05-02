# VibePulse Mobile

Expo + React Native + TypeScript client for the VibePulse REST API.

## Prerequisites

- Node 18+ and npm
- Expo Go (iOS/Android), or build a custom dev client
- The VibePulse API running locally (default: `http://localhost:8000`)

## Setup

```bash
cd apps/mobile
npm install
```

## Configure the API base URL

`app.json` -> `expo.extra.apiBaseUrl`

```json
"extra": {
  "apiBaseUrl": "http://localhost:8000/api/v1"
}
```

For physical devices, `localhost` won't reach your laptop. Use the LAN IP
of the machine running the API instead, e.g. `http://192.168.1.42:8000/api/v1`.
You can find it with `ipconfig getifaddr en0` on macOS.

## Run

```bash
npm run start:dev   # expo start --dev-client
# or
npm run ios
npm run android
```

Then scan the QR code with Expo Go (or your custom dev client).

## Stack

- expo-router (file-based routing)
- @tanstack/react-query (server state)
- zustand (client state, tokens)
- axios (HTTP, with 401-refresh interceptor)
- AsyncStorage (token persistence)
- zod + react-hook-form (forms)

## Routes

- `/` auth gate (decides login vs missions)
- `/(auth)/login`, `/(auth)/register`
- `/(app)/missions` list
- `/(app)/missions/new` create form
- `/(app)/missions/[id]` overview / members
- `/(app)/missions/[id]/preferences`
- `/(app)/missions/[id]/places`
- `/(app)/missions/[id]/rankings`
- `/(app)/missions/[id]/vote`
- `/(app)/missions/[id]/runs` (HITL approve/reject)

## Caveats

- Tap-to-set map location is deferred. Mission create defaults to Atlanta
  (33.7490, -84.3880).
- expo-location, react-native-maps, expo-notifications are intentionally
  not included; add them in a later milestone.
