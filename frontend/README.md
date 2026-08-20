# netbot — frontend

Next.js implementation of the netbot design: grounded RAG chat with face unlock
and two-way voice, built for NETSOL.

## Getting started

```bash
cd frontend
npm install
npm run dev
```

The app runs at http://localhost:3000.

## Scripts

| Script              | What it does                          |
| ------------------- | ------------------------------------- |
| `npm run dev`       | Dev server with hot reload            |
| `npm run build`     | Production build                      |
| `npm run start`     | Serve the production build            |
| `npm run typecheck` | Type-check without emitting           |

## Routes

| Route               | Screen                                                          |
| ------------------- | --------------------------------------------------------------- |
| `/`                 | Landing page with live previews of every screen                  |
| `/signin`           | Split-screen sign in, password plus Face ID                      |
| `/enroll`           | Three-step face enrollment with capture progress                 |
| `/chat`             | Workspace: history sidebar, messages, sources rail               |
| `/settings/profile` | Profile, avatar picker, account and session actions              |

The landing page embeds the same interactive components used by the standalone
routes, so the previews are live rather than screenshots.

## Structure

```
src/
├── app/                    # App Router routes
│   ├── layout.tsx          # Root layout, nav, theme provider
│   ├── page.tsx            # Landing page
│   ├── chat/
│   ├── enroll/
│   ├── signin/
│   └── settings/profile/
├── components/
│   ├── chat/               # Sidebar, message list, composer, sources rail
│   ├── screens/            # One component per full screen
│   ├── BrowserFrame.tsx
│   ├── NetsolLogo.tsx
│   ├── SiteFooter.tsx
│   ├── ThemeToggle.tsx
│   ├── TopNav.tsx
│   └── Wordmark.tsx
├── lib/
│   ├── data.ts             # Mock conversations, sources, user
│   ├── theme.tsx           # Theme context and no-flash boot script
│   └── useSpeech.ts        # Dictation and read-aloud hooks
└── styles/                 # Design tokens and per-area stylesheets
```

## Theming

Light and dark are driven by CSS custom properties on `:root[data-theme]`.
An inline script in the root layout applies the stored or system-preferred theme
before first paint, so there is no flash of the wrong palette. The choice
persists in `localStorage`.

## Voice

The composer microphone uses the Web Speech API for dictation, and answers can
be read back with speech synthesis. Browsers without those APIs still show the
listening animation, so nothing looks broken.

## Connecting a backend

The UI currently runs on mock data in `src/lib/data.ts`. To wire up the real
service, replace `draftAnswer()` with a call to the retrieval endpoint and swap
`CONVERSATIONS` for fetched data. The face enrollment screen simulates capture
progress and is ready to be pointed at a camera stream and enrollment API.
