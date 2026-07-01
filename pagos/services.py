import hashlib
import json
import logging
import uuid

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class WompiError(Exception):
    """Error genérico al comunicarse con la API de Wompi."""


def generar_referencia(prefijo: str = "ORDRAE") -> str:
    """Referencia única de pago (Wompi no permite reutilizar una ya usada)."""
    return f"{prefijo}-{uuid.uuid4().hex[:16].upper()}"


def generar_firma_integridad(referencia: str, amount_in_cents: int, moneda: str = "COP") -> str:
    """
    SHA256(referencia + amount_in_cents + moneda + secreto_integridad).
    El ORDEN de concatenación es exacto según la documentación de Wompi:
    https://docs.wompi.co/docs/colombia/widget-checkout-web/
    NUNCA generar esto en el frontend: expondría el secreto de integridad.
    """
    secreto = settings.WOMPI_INTEGRITY_SECRET
    cadena = f"{referencia}{amount_in_cents}{moneda}{secreto}"
    return hashlib.sha256(cadena.encode("utf-8")).hexdigest()


def verificar_checksum_evento(event: dict) -> bool:
    """
    Valida la firma de un evento (webhook) de Wompi.
    checksum = SHA256( valores de signature.properties en orden + timestamp + WOMPI_EVENTS_SECRET )
    https://docs.wompi.co/docs/colombia/eventos/
    """
    try:
        signature = event["signature"]
        properties = signature["properties"]
        checksum_recibido = signature["checksum"]
        timestamp = event["timestamp"]
    except KeyError:
        return False

    data_obj = event.get("data", {})
    valores = []
    for prop in properties:
        valor = data_obj
        for parte in prop.split("."):
            valor = valor.get(parte) if isinstance(valor, dict) else None
        valores.append(str(valor))

    cadena = "".join(valores) + str(timestamp) + settings.WOMPI_EVENTS_SECRET
    checksum_calculado = hashlib.sha256(cadena.encode("utf-8")).hexdigest()
    return checksum_calculado.upper() == str(checksum_recibido).upper()


def consultar_transaccion(transaction_id: str) -> dict:
    """
    GET /v1/transactions/{id}
    Fuente de verdad del estado del pago — nunca confiar en lo que reporte el frontend.
    """
    url = f"{settings.WOMPI_BASE_URL}/transactions/{transaction_id}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json().get("data", {})
    except requests.RequestException as e:
        logger.error(f"Error consultando transacción Wompi {transaction_id}: {e}")
        raise WompiError(str(e))


def verificar_merchant(public_key: str) -> dict:
    """GET /v1/merchants/{public_key} — healthcheck de configuración (usado en debug_wompi)."""
    url = f"{settings.WOMPI_BASE_URL}/merchants/{public_key}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json().get("data", {})