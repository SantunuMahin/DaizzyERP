"""
Custom application exceptions and DRF exception handler.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger('apps.exceptions')


class BaseBusinessError(Exception):
    """Base class for domain business exceptions."""
    default_code = 'BUSINESS_ERROR'
    default_status = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str, code: str = None, status_code: int = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.status_code = status_code or self.default_status
        self.details = details or {}


class InsufficientStockError(BaseBusinessError):
    default_code = 'INSUFFICIENT_STOCK'
    default_status = status.HTTP_409_CONFLICT

    def __init__(self, product_id, available, requested, product_name: str = None):
        target = f"'{product_name}'" if product_name else f"product ID {product_id}"
        msg = f"Insufficient stock for {target}. Available: {available}, Requested: {requested}"
        super().__init__(msg, details={
            'product_id': product_id,
            'product_name': product_name or str(product_id),
            'available': available,
            'requested': requested
        })


class DuplicateBarcodeError(BaseBusinessError):
    default_code = 'DUPLICATE_BARCODE'
    default_status = status.HTTP_409_CONFLICT

    def __init__(self, barcode: str):
        msg = f"Barcode '{barcode}' is already assigned to another active product."
        super().__init__(msg, details={'barcode': barcode})


class DuplicateInvoiceError(BaseBusinessError):
    default_code = 'DUPLICATE_INVOICE'
    default_status = status.HTTP_409_CONFLICT


class InvalidSaleOperationError(BaseBusinessError):
    default_code = 'INVALID_SALE_OPERATION'
    default_status = status.HTTP_400_BAD_REQUEST


class ReturnQuantityExceededError(BaseBusinessError):
    default_code = 'RETURN_QUANTITY_EXCEEDED'
    default_status = status.HTTP_409_CONFLICT


class PaymentValidationError(BaseBusinessError):
    default_code = 'PAYMENT_VALIDATION_ERROR'
    default_status = status.HTTP_400_BAD_REQUEST


def custom_exception_handler(exc, context):
    """
    Standardize all DRF and business exception responses to envelope:
    {
      "success": false,
      "error": {
        "code": "...",
        "message": "...",
        "details": {}
      }
    }
    """
    if isinstance(exc, BaseBusinessError):
        return Response({
            'success': False,
            'error': {
                'code': exc.code,
                'message': exc.message,
                'details': exc.details,
            }
        }, status=exc.status_code)

    response = exception_handler(exc, context)

    if response is not None:
        error_code = getattr(exc, 'default_code', 'VALIDATION_ERROR')
        message = 'A request validation or processing error occurred.'

        if isinstance(response.data, dict) and 'detail' in response.data:
            message = str(response.data['detail'])

        response.data = {
            'success': False,
            'error': {
                'code': str(error_code).upper(),
                'message': message,
                'details': response.data if 'detail' not in response.data else {},
            }
        }
    else:
        logger.exception("Unhandled server exception encountered: %s", exc)
        return Response({
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An internal system error occurred. Please contact support.',
                'details': {},
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response
