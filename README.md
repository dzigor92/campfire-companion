# Campfire Companion (Python + React Rebuild)

This repo is the groundwork for recreating Campfire Tools with a Django REST backend and a modern React frontend.

## Project Layout

```
backend/   # Django project (campfire_backend) + api app + requirements.txt
frontend/  # Vite + React single-page app, API client, and styling
```

## Backend (Django)

1. Create & activate a virtual environment (recommended).
2. Install dependencies:
   ```bash
   cd backend
   python3 -m pip install -r requirements.txt
   ```
3. Apply migrations and run the dev server:
   ```bash
   python3 manage.py migrate
   python3 manage.py runserver 0.0.0.0:8000
   ```
4. Verify the API via `GET http://127.0.0.1:8000/api/health/` (the React app calls this on load).

Key packages already wired up:
- `djangorestframework` for building JSON APIs.
- `django-cors-headers` for local cross-origin requests.

## Frontend (React + Vite)

1. Copy the provided env template and adjust if needed:
   ```bash
   cd frontend
   cp .env.example .env
   ```
2. Install JS dependencies and start the dev server:
   ```bash
   npm install
   npm run dev
   ```
3. Visit the URL printed by Vite (default `http://localhost:5173`). The hero section, feature cards, and health-status widget show how to talk to the Django API.

> **Node version:** Vite 7 targets Node ≥ 20.19.0. Builds succeed on Node 18 with warnings, but upgrading Node is recommended for local development.

## Next Steps

- Model real data in new Django apps (e.g., trips, checklists, resources) and expose DRF viewsets.
- Replace the placeholder React content with routed pages, shared layout components, and API hooks.
- Add Docker/compose or Procfile-based tooling once the data model stabilizes.
