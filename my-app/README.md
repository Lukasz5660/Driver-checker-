# Driver Checker

Driver Checker is a lightweight starter kit that combines a React + TypeScript + Vite
frontend with a Python Flask backend. Use it as a foundation for building a richer driver
monitoring or telematics experience.

## Project structure

```
my-app/
├── backend/            # Flask backend service
│   ├── app.py          # Application entry point and routes
│   └── requirements.txt
├── public/
├── src/                # React application source
└── vite.config.ts      # Vite configuration (includes API proxy for development)
```

## Prerequisites

- [Node.js](https://nodejs.org/) 18 or newer
- [Python](https://www.python.org/) 3.10 or newer

## Backend (Flask)

Install dependencies and run the server:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r backend/requirements.txt
python backend/app.py
```

The backend listens on `http://localhost:5000` by default and exposes a simple health
endpoint at `GET /api/status`.

### Configuration

The backend recognises the following environment variables:

| Variable          | Description                                                                 |
| ----------------- | --------------------------------------------------------------------------- |
| `PORT`            | Overrides the default port (`5000`).                                       |
| `FRONTEND_ORIGIN` | Restricts CORS access to the provided origin (defaults to allowing all).    |

## Frontend (React + Vite)

Install dependencies and start the development server:

```bash
npm install
npm run dev
```

The Vite dev server proxies `/api` requests to the Flask backend. For production builds or
when the backend runs on another host, set the `VITE_API_BASE_URL` environment variable in
an `.env` file:

```
VITE_API_BASE_URL=http://localhost:5000
```

Then build the frontend with:

```bash
npm run build
```

## Development workflow

1. Start the Flask backend (`python backend/app.py`).
2. In another terminal, run the React dev server (`npm run dev`).
3. Visit the URL printed by Vite (usually `http://localhost:5173`) to see the frontend
   displaying the backend health status.

## Available API routes

| Method | Route         | Description                     |
| ------ | ------------- | ------------------------------- |
| GET    | `/api/status` | Returns the backend health info |

This structure gives you a solid jumping-off point for building out your own Driver
Checker features.
