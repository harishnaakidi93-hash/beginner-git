# Maison Restaurant Portal

A React + Flask restaurant operations portal for a 12-person kitchen team. It includes weekly shift planning, weekly days off, daily meal and dessert updates, and employee meal requests.

## Team

- 2 managers
- 2 chefs de cuisine
- 2 chefs de second
- 6 commis de cuisine

## Run locally

### 1. Configure authentication

Create the environment file from the example:

```bash
cp .env.example .env
```

Replace `AUTH_USERNAME`, `AUTH_PASSWORD`, and `FLASK_SECRET_KEY` with strong values. The `.env` file is ignored by Git and is never committed.

Users can sign up with email and password, sign in with Google or Facebook when OAuth credentials are configured, and request a password reset. Password reset requires SMTP settings. The administrator account is created automatically from the environment configuration.

### 2. Install the Python API

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python backend/app.py
```

The API runs on http://127.0.0.1:5000 and creates restaurant.db automatically. The portal requires authentication before showing restaurant data.

### 3. Install and run React

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173. The Vite development server proxies API requests to Flask.

## Production build

```bash
cd frontend
npm install
npm run build
cd ..
python backend/app.py
```

Flask serves the generated frontend from the backend. The database is stored at restaurant.db and is ignored by Git.

## Deployment

The application is ready to deploy as a Flask application. Configure the values in `.env`, install the Python dependencies, run the production build, then start the server with:

```bash
python backend/app.py
```

For production, set `FLASK_ENV=production`, use HTTPS, and keep the generated `.env` file private. The application uses HTTP-only session cookies, password hashing, and OAuth authorization-code authentication.

Google and Facebook OAuth require credentials from their developer dashboards. Password reset requires an SMTP server and a public `APP_URL` that matches the deployed backend.

For a Git clone, use:

```bash
git clone <repository-url>
cd Restaurant-Portal
```

No Docker is required.

## Database

SQLite is used so the application does not require a separate database service. The backend creates the schema and sample team schedule when the application starts. Data is updated automatically through the REST API.
