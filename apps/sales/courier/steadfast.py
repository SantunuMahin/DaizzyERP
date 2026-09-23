"""
Steadfast Courier Integration Client.
Official API documentation: https://portal.steadfast.com.bd/api/v1

Provides consignment booking, status tracking, balance lookup, and simulation fallback.
"""
import json
import logging
import urllib.request
import urllib.error
from decimal import Decimal
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

STEADFAST_DEFAULT_BASE_URL = "https://portal.steadfast.com.bd/api/v1"


class SteadfastCourierService:
    """
    Steadfast Courier API Service.
    Interacts with Steadfast portal for automated COD consignment creation and status tracking.
    """

    @classmethod
    def get_config(cls):
        """Fetch courier configuration from database or settings."""
        try:
            from .models import CourierConfig
            cfg = CourierConfig.objects.filter(courier_name='steadfast').first()
            if cfg:
                return {
                    'api_key': cfg.api_key.strip(),
                    'secret_key': cfg.secret_key.strip(),
                    'base_url': cfg.base_url.strip() or STEADFAST_DEFAULT_BASE_URL,
                    'is_active': cfg.is_active,
                    'auto_send_on_confirm': cfg.auto_send_on_confirm,
                    'test_mode': cfg.test_mode,
                }
        except Exception as e:
            logger.warning(f"Could not load CourierConfig from DB: {e}")

        # Fallback to django settings or environment
        return {
            'api_key': getattr(settings, 'STEADFAST_API_KEY', ''),
            'secret_key': getattr(settings, 'STEADFAST_SECRET_KEY', ''),
            'base_url': getattr(settings, 'STEADFAST_BASE_URL', STEADFAST_DEFAULT_BASE_URL),
            'is_active': True,
            'auto_send_on_confirm': getattr(settings, 'STEADFAST_AUTO_DISPATCH', True),
            'test_mode': getattr(settings, 'STEADFAST_TEST_MODE', False),
        }

    @classmethod
    def _make_request(cls, endpoint: str, method: str = 'GET', data: dict = None) -> dict:
        """Execute HTTP request to Steadfast API."""
        cfg = cls.get_config()
        api_key = cfg.get('api_key')
        secret_key = cfg.get('secret_key')
        base_url = cfg.get('base_url', STEADFAST_DEFAULT_BASE_URL).rstrip('/')

        # Check if credentials exist or if in test/simulation mode
        if not api_key or not secret_key or cfg.get('test_mode'):
            logger.info("Steadfast credentials missing or test mode active — using simulation handler.")
            return cls._simulate_response(endpoint, method, data)

        url = f"{base_url}{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'Api-Key': api_key,
            'Secret-Key': secret_key,
            'User-Agent': 'Daizzy-ERP-Steadfast-Connector/2.0',
        }

        body_bytes = None
        if data is not None:
            body_bytes = json.dumps(data).encode('utf-8')

        req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_text = resp.read().decode('utf-8')
                return json.loads(resp_text)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='ignore')
            logger.error(f"Steadfast HTTP Error {e.code}: {err_body}")
            try:
                err_json = json.loads(err_body)
                return {'status': e.code, 'error': True, 'message': err_json.get('message', str(e)), 'raw': err_json}
            except Exception:
                return {'status': e.code, 'error': True, 'message': f"HTTP Error {e.code}: {err_body}"}
        except Exception as e:
            logger.error(f"Steadfast connection failure: {e}")
            return {'status': 500, 'error': True, 'message': str(e)}

    @classmethod
    def _simulate_response(cls, endpoint: str, method: str, data: dict = None) -> dict:
        """Simulates response for offline testing or pre-configured demonstrations."""
        import random
        now_ts = timezone.now().strftime("%Y%m%d%H%M")
        random_num = random.randint(100000, 999999)

        if '/create_order' in endpoint:
            invoice = data.get('invoice', f'INV-{now_ts}')
            consignment_id = f"C{random_num}"
            tracking_code = f"STDF{random_num}"
            return {
                'status': 200,
                'message': 'Order created successfully (Simulated mode).',
                'consignment': {
                    'consignment_id': consignment_id,
                    'invoice': invoice,
                    'tracking_code': tracking_code,
                    'recipient_name': data.get('recipient_name', ''),
                    'recipient_phone': data.get('recipient_phone', ''),
                    'recipient_address': data.get('recipient_address', ''),
                    'cod_amount': data.get('cod_amount', 0),
                    'status': 'in_review',
                    'note': data.get('note', ''),
                    'tracking_url': f"https://steadfast.com.bd/t/{tracking_code}",
                    'created_at': timezone.now().isoformat(),
                }
            }

        elif '/status_by_cid' in endpoint or '/status_by_invoice' in endpoint:
            statuses = ['in_review', 'pending', 'in_transit', 'delivered', 'partial_delivered']
            selected_status = 'in_transit'
            return {
                'status': 200,
                'delivery_status': selected_status,
                'status_display': 'In Transit (Simulated)',
                'message': 'Consignment status fetched successfully.',
            }

        elif '/get_balance' in endpoint:
            return {
                'status': 200,
                'current_balance': 48500.00,
                'currency': 'BDT',
                'message': 'Account active and connected.',
            }

        return {'status': 200, 'message': 'Simulated response OK.'}

    @classmethod
    def create_order(cls, invoice: str, recipient_name: str, recipient_phone: str,
                     recipient_address: str, cod_amount: float or Decimal,
                     note: str = '') -> dict:
        """
        Creates a new delivery order in Steadfast Courier.
        Args:
            invoice: Unique Invoice Number (e.g. INV-20260923-0001)
            recipient_name: Customer Name
            recipient_phone: 11-digit Bangladesh phone number
            recipient_address: Complete delivery street address
            cod_amount: Cash on Delivery amount to collect in BDT
            note: Delivery note / fragile / call instruction
        Returns:
            Dict containing consignment details, consignment_id, tracking_code, etc.
        """
        # Clean inputs
        phone = recipient_phone.replace(' ', '').replace('-', '')
        if phone.startswith('+88'):
            phone = phone[3:]
        elif phone.startswith('88'):
            phone = phone[2:]

        payload = {
            'invoice': str(invoice),
            'recipient_name': str(recipient_name or 'Valued Customer').strip(),
            'recipient_phone': phone.strip(),
            'recipient_address': str(recipient_address or 'Dhaka, Bangladesh').strip(),
            'cod_amount': float(cod_amount or 0.0),
            'note': str(note or 'Please call customer before delivery. Daizzy ERP').strip(),
        }

        resp = cls._make_request('/create_order', method='POST', data=payload)
        return resp

    @classmethod
    def get_status_by_cid(cls, consignment_id: str) -> dict:
        """Retrieve live delivery status by Steadfast Consignment ID."""
        if not consignment_id:
            return {'status': 400, 'error': True, 'message': 'Consignment ID required'}
        return cls._make_request(f'/status_by_cid/{consignment_id}', method='GET')

    @classmethod
    def get_status_by_invoice(cls, invoice: str) -> dict:
        """Retrieve live delivery status by Store Invoice Number."""
        if not invoice:
            return {'status': 400, 'error': True, 'message': 'Invoice number required'}
        return cls._make_request(f'/status_by_invoice/{invoice}', method='GET')

    @classmethod
    def get_account_balance(cls) -> dict:
        """Retrieve current Steadfast account COD balance."""
        return cls._make_request('/get_balance', method='GET')

    @classmethod
    def get_tracking_url(cls, tracking_code: str) -> str:
        """Generate direct public tracking URL for Steadfast."""
        if not tracking_code:
            return 'https://steadfast.com.bd'
        return f"https://steadfast.com.bd/t/{tracking_code}"
