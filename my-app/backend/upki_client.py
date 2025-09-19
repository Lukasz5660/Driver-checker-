"""Utilities for interacting with the UPKI SOAP service."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from requests import Session
from requests.exceptions import RequestException
from zeep import Client, Settings
from zeep.exceptions import Fault
from zeep.helpers import serialize_object
from zeep.transports import Transport
from zeep.wsse.signature import Signature

__all__ = [
    "UpkiClientError",
    "UpkiConfigurationError",
    "UpkiServiceError",
    "call_pytanie_o_uprawnienia",
]


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UpkiConfig:
    """Configuration required to communicate with the UPKI service."""

    wsdl_path: str
    service_endpoint: str
    tls_cert_pem: str
    tls_key_pem: str
    ca_bundle: Optional[str]
    wsse_key_pem: str
    wsse_cert_pem: str
    connect_timeout: float
    read_timeout: float
    debug_soap: bool


class UpkiClientError(Exception):
    """Base exception for UPKI client errors."""


class UpkiConfigurationError(UpkiClientError):
    """Raised when required configuration is missing or invalid."""


class UpkiServiceError(UpkiClientError):
    """Raised when the UPKI service responds with a SOAP fault."""

    def __init__(self, message: str, fault_code: Optional[str] = None, details: Any | None = None):
        super().__init__(message)
        self.fault_code = fault_code
        self.details = details


def load_config() -> UpkiConfig:
    """Load configuration from environment variables."""

    wsdl_path = os.environ.get(
        "UPKI_WSDL_PATH",
        r"C:\\APIUprawnieniaKierowcow\\wsdl.ul.uprawnienia-kierowcow.przewoznicy-1.0.1\\wsdl-xsd\\uprawnienia-kierowcow.przewoznicy.wsdl",
    )
    service_endpoint = os.environ.get(
        "UPKI_ENDPOINT_URL",
        "https://185.41.93.94:6455/cepik/api/ul/UprawnieniaKierowcowPrzewoznicyService",
    )
    tls_cert_pem = os.environ.get(
        "UPKI_TLS_CERT_PEM",
        r"C:\\APIUprawnieniaKierowcow\\cert\\client_tls_cert.pem",
    )
    tls_key_pem = os.environ.get(
        "UPKI_TLS_KEY_PEM",
        r"C:\\APIUprawnieniaKierowcow\\cert\\client_tls_key.pem",
    )
    ca_bundle = os.environ.get("UPKI_CA_BUNDLE")
    wsse_key_pem = os.environ.get(
        "UPKI_WSSE_KEY_PEM",
        r"C:\\APIUprawnieniaKierowcow\\cert\\wsse_key.pem",
    )
    wsse_cert_pem = os.environ.get(
        "UPKI_WSSE_CERT_PEM",
        r"C:\\APIUprawnieniaKierowcow\\cert\\wsse_cert.pem",
    )

    try:
        connect_timeout = float(os.environ.get("UPKI_CONNECT_TIMEOUT", "10"))
    except ValueError as exc:
        raise UpkiConfigurationError("UPKI_CONNECT_TIMEOUT must be a numeric value") from exc

    try:
        read_timeout = float(os.environ.get("UPKI_READ_TIMEOUT", "20"))
    except ValueError as exc:
        raise UpkiConfigurationError("UPKI_READ_TIMEOUT must be a numeric value") from exc

    debug_soap = os.environ.get("UPKI_DEBUG", "0") in {"1", "true", "True"}

    for env_var, path in (
        ("UPKI_TLS_CERT_PEM", tls_cert_pem),
        ("UPKI_TLS_KEY_PEM", tls_key_pem),
        ("UPKI_WSSE_KEY_PEM", wsse_key_pem),
        ("UPKI_WSSE_CERT_PEM", wsse_cert_pem),
    ):
        if not path:
            raise UpkiConfigurationError(f"Environment variable {env_var} must be set")
        if "://" not in path and not os.path.exists(path):
            raise UpkiConfigurationError(f"File not found for {env_var}: {path}")

    if ca_bundle and "://" not in ca_bundle and not os.path.exists(ca_bundle):
        raise UpkiConfigurationError(f"File not found for UPKI_CA_BUNDLE: {ca_bundle}")

    if not wsdl_path:
        raise UpkiConfigurationError("Environment variable UPKI_WSDL_PATH must be set")
    if "://" not in wsdl_path and not os.path.exists(wsdl_path):
        raise UpkiConfigurationError(f"WSDL file not found: {wsdl_path}")

    return UpkiConfig(
        wsdl_path=wsdl_path,
        service_endpoint=service_endpoint,
        tls_cert_pem=tls_cert_pem,
        tls_key_pem=tls_key_pem,
        ca_bundle=ca_bundle,
        wsse_key_pem=wsse_key_pem,
        wsse_cert_pem=wsse_cert_pem,
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
        debug_soap=debug_soap,
    )


def build_transport(config: UpkiConfig) -> Transport:
    """Construct a Zeep transport with mutual TLS support."""

    session: Session = requests.Session()
    session.cert = (config.tls_cert_pem, config.tls_key_pem)
    if config.ca_bundle:
        session.verify = config.ca_bundle
    else:
        session.verify = True
    return Transport(session=session)


def build_client(config: UpkiConfig) -> Client:
    """Create a Zeep client configured for WS-Security signatures."""

    if config.debug_soap:
        logging.getLogger("zeep").setLevel(logging.DEBUG)

    wsse = Signature(config.wsse_key_pem, config.wsse_cert_pem)
    settings = Settings(strict=True, xml_huge_tree=True)
    transport = build_transport(config)
    return Client(wsdl=config.wsdl_path, transport=transport, wsse=wsse, settings=settings)


def _create_service_proxy(client: Client, endpoint: str):
    """Create a Zeep service proxy targeting a specific endpoint."""

    try:
        binding_name = next(iter(client.wsdl.bindings))
    except StopIteration as exc:
        raise UpkiConfigurationError("The provided WSDL does not define any bindings") from exc
    return client.create_service(binding_name, endpoint)


def _serialize_detail(detail: Any) -> Any:
    """Best-effort serialization of SOAP fault details."""

    if detail is None:
        return None

    try:
        return serialize_object(detail)
    except Exception:  # pragma: no cover - zeep detail serialization is best effort
        return str(detail)


def call_pytanie_o_uprawnienia(
    imie_pierwsze: str,
    nazwisko: str,
    seria_numer_blankietu: str,
) -> Dict[str, Any]:
    """Invoke the ``pytanieOUprawnienia`` operation and return the response payload."""

    if not imie_pierwsze or not nazwisko or not seria_numer_blankietu:
        raise UpkiClientError("All parameters must be provided for the UPKI request")

    config = load_config()
    client = build_client(config)
    service = _create_service_proxy(client, config.service_endpoint)

    request_obj = {
        "imiePierwsze": imie_pierwsze,
        "nazwisko": nazwisko,
        "seriaNumerBlankietuDruku": seria_numer_blankietu,
    }

    try:
        response = service.pytanieOUprawnienia(
            DaneDokumentuRequest=request_obj,
            _timeout=(config.connect_timeout, config.read_timeout),
        )
        return serialize_object(response)
    except Fault as fault:
        logger.exception("UPKI SOAP fault encountered")
        detail = _serialize_detail(getattr(fault, "detail", None))
        raise UpkiServiceError(
            message=str(fault),
            fault_code=getattr(fault, "faultcode", None),
            details=detail,
        ) from fault
    except RequestException as exc:
        logger.exception("Network error during UPKI request")
        raise UpkiClientError("Failed to communicate with the UPKI service") from exc
    except OSError as exc:
        logger.exception("Certificate or key file could not be read")
        raise UpkiClientError("Failed to read certificate or key files required for UPKI access") from exc
