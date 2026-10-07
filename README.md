# Maison Restaurant Portal

A React + Flask restaurant operations portal for a 12-person kitchen team. It includes weekly shift planning, weekly days off, daily meal and dessert updates, and employee meal requests.

## Team

- 2 managers
- 2 chefs de cuisine
- 2 chefs de second
- 6 commis de cuisine

## Run locally

### 1. Install the Python API

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python backend/app.py
```

The API runs on http://127.0.0.1:5000 and creates restaurant.db automatically.

### 2. Install and run React

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

The project is ready to deploy as a Flask application. Install the Python dependencies, run the production build, then start the server with:

```bash
python backend/app.py
```

For a Git clone, use:

```bash
git clone <repository-url>
cd Restaurant-Portal
```

No Docker is required.

## Database

SQLite is used so the application does not require a separate database service. The backend creates the schema and sample team schedule when the application starts. Data is updated automatically through the REST API.
