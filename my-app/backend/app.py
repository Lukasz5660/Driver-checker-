"""Flask application powering the Driver Checker backend."""
from __future__ import annotations

import os
from typing import Any, Dict

from flask import Flask, jsonify
from flask_cors import CORS


def create_app() -> Flask:
    """Create and configure the Flask application instance."""
    app = Flask(__name__)

    cors_origin = os.getenv("FRONTEND_ORIGIN")
    cors_resources: Dict[str, Dict[str, Any]] = {
        r"/api/*": {"origins": cors_origin or "*"}
    }
    CORS(app, resources=cors_resources)

    @app.get("/api/status")
    def status() -> Any:
        """Report the health of the backend service."""
        return jsonify(
            {
                "service": "Driver Checker API",
                "status": "ok",
                "message": "Flask backend is running and reachable.",
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
