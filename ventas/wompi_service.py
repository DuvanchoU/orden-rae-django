# ventas/wompi_service.py
import requests
import hashlib
import hmac
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class WompiService:
    """
    Servicio de integración con Wompi
    Soporta modo sandbox y producción
    """
    
    def __init__(self):
        self.base_url = settings.WOMPI_BASE_URL
        self.private_key = settings.WOMPI_PRIVATE_KEY
        self.public_key = settings.WOMPI_PUBLIC_KEY
        self.integrity_secret = settings.WOMPI_INTEGRITY_SECRET
        self.is_sandbox = 'sandbox' in self.base_url
    
    def crear_transaccion(self, venta, referencia):
        """
        Crear transacción en Wompi
        Retorna: dict con datos de la transacción o None
        """
        url = f"{self.base_url}/transactions"
        
        # Wompi requiere el monto en centavos
        monto_centavos = int(float(venta.total) * 100)
        
        data = {
            'amount_in_cents': monto_centavos,
            'currency': 'COP',
            'customer_email': venta.cliente.email if venta.cliente else '',
            'reference': referencia,
            'redirect_url': f'{settings.SITE_URL}/ventas/pago/wompi/confirmacion/{venta.id_venta}/',
        }
        
        headers = {
            'Authorization': f'Bearer {self.private_key}',
            'Content-Type': 'application/json',
        }
        
        try:
            logger.info(f"Creando transacción Wompi: {referencia} - Monto: ${venta.total}")
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            resultado = response.json()
            
            logger.info(f"Transacción creada exitosamente: {resultado.get('data', {}).get('id')}")
            return resultado
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creando transacción Wompi: {e}")
            return None
    
    def consultar_transaccion(self, transaction_id):
        """Consultar estado de transacción en Wompi"""
        url = f"{self.base_url}/transactions/{transaction_id}"
        
        headers = {
            'Authorization': f'Bearer {self.private_key}',
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error consultando transacción: {e}")
            return None
    
    def verificar_webhook(self, payload, signature):
        """Verificar que el webhook viene de Wompi"""
        if not self.integrity_secret:
            logger.warning("WOMPI_INTEGRITY_SECRET no configurado")
            return False
        
        expected_signature = hmac.new(
            self.integrity_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    
    def generar_referencia(self, venta_id):
        """Generar referencia única para la transacción"""
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        return f"ORD-{venta_id}-{timestamp}"