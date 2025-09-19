"""Flask application powering the Driver Checker backend."""
from __future__ import annotations

import os
from typing import Any, Dict

from flask import Flask, jsonify, request
from flask_cors import CORS

from upki_client import (
    UpkiClientError,
    UpkiConfigurationError,
    UpkiServiceError,
    call_pytanie_o_uprawnienia,
)


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

    @app.post("/api/upki/pytanie")
    def pytanie_o_uprawnienia_endpoint() -> Any:
        """Proxy the UPKI ``pytanieOUprawnienia`` SOAP operation."""

        payload = request.get_json(silent=True)
        if payload is None:
            return (
                jsonify({"error": "Request body must be valid JSON."}),
                400,
            )

        required_fields = [
            "imiePierwsze",
            "nazwisko",
            "seriaNumerBlankietuDruku",
        ]
        missing = [field for field in required_fields if not payload.get(field)]
        if missing:
            return (
                jsonify(
                    {
                        "error": "Missing required request fields.",
                        "fields": missing,
                    }
                ),
                400,
            )

        try:
            result = call_pytanie_o_uprawnienia(
                payload["imiePierwsze"],
                payload["nazwisko"],
                payload["seriaNumerBlankietuDruku"],
            )
        except UpkiConfigurationError as exc:
            app.logger.error("UPKI configuration error: %s", exc)
            return jsonify({"error": str(exc)}), 500
        except UpkiServiceError as exc:
            app.logger.warning("UPKI service fault: %s", exc)
            error_body: Dict[str, Any] = {"error": str(exc)}
            if exc.fault_code:
                error_body["faultCode"] = exc.fault_code
            if exc.details is not None:
                error_body["details"] = exc.details
            return jsonify(error_body), 502
        except UpkiClientError as exc:
            app.logger.error("UPKI client error: %s", exc)
            return jsonify({"error": str(exc)}), 502

        return jsonify({"data": result})

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
