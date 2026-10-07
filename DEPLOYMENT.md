# Deployment guide

## Linux server

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
4. Build the frontend:
   ```bash
   cd frontend && npm install && npm run build
   ```
5. Start Flask with a system service, or run it directly:
   ```bash
   cd /path/to/Restaurant-Portal
   python backend/app.py
   ```

The application listens on port 5000 by default. Set `PORT=5001` when a different port is required.

## Systemd example

Create `/etc/systemd/system/restaurant-portal.service` with the Flask process running as the service account. The service working directory must be the project root, and `ExecStart` should point to the virtual environment's Python interpreter.

The SQLite database is created at `restaurant.db` in the project root. Keep this file in a persistent location if the service is moved or restarted.

## Reverse proxy

Serve the Flask application behind Nginx or Caddy. The backend should receive `/api/*` requests and the frontend should be served from the same Flask application.

## Database backup

Copy `restaurant.db` while Flask is stopped, or use SQLite backup tooling. The database is automatically created and seeded on first startup.
