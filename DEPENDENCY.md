# Authentication and Security Notes

The portal requires a server-side authenticated session before any API data is returned.

- The administrator username and password are loaded from environment variables.
- Passwords are verified using Werkzeug password hashing.
- Sessions use HTTP-only, SameSite cookies.
- Secure cookies are enabled when `FLASK_ENV=production`.
- The application can be configured with a session timeout in `SESSION_TIMEOUT_HOURS`.
- The `.env` file and SQLite database are excluded from Git.

Before starting the application, copy `.env.example` to `.env` and replace the example values.

```bash
cp .env.example .env
openssl rand -hex 32
```

Do not commit `.env` or share its contents. On a public server, place the application behind HTTPS and configure the reverse proxy to provide the correct host and secure-cookie settings.
