# Deploy NetBot frontend on Vercel

> Commits that trigger Vercel must be authored by the Vercel project owner on Hobby (private repos).

The GitHub repo is a **monorepo**. The website is only in `frontend/`.
If Vercel builds the repo root as Next.js, you get **`404: NOT_FOUND`**.

## Important

- The browser message about **Content Security Policy / eval** is **not** from NetBot.
  Our app does not set a CSP. That warning usually comes from an extension or DevTools.
  It is **not** the reason for the Vercel 404.

## Fix A — Root Directory = `frontend` (best)

1. Open the **project** in Vercel (not only the live URL).
2. **Settings** → **Build and Deployment**.
3. **Root Directory** → **Edit** → type `frontend` → **Save**.
4. **Framework Preset** → **Next.js**.
5. Clear any custom Build / Output overrides (use defaults).
6. **Deployments** → **Redeploy** the latest `dev` commit.

## Fix B — Keep Root Directory empty (use repo-root `vercel.json`)

1. **Settings** → **Build and Deployment**.
2. **Framework Preset** → **Other** (turn Override **ON**).
3. **Install Command** Override ON → `npm install --prefix frontend`
4. **Build Command** Override ON → `npm run build --prefix frontend`
5. **Output Directory** Override ON → `frontend/out`
6. **Redeploy**.

## After deploy

- Latest deployment must show **Ready** (green), not Error.
- Open that deployment’s URL first, then check the production domain.
- Set env var `NEXT_PUBLIC_API_URL` to your **hosted** FastAPI URL (not `localhost`).
