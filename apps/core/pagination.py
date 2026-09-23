"""
Custom pagination classes with standardized metadata envelopes.
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
import math


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination for DRF endpoints.
    Produces:
    {
      "success": true,
      "data": [...],
      "meta": {
        "page": 1,
        "page_size": 20,
        "total": 100,
        "total_pages": 5,
        "next": "...",
        "previous": "..."
      }
    }
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        total_items = self.page.paginator.count
        total_pages = math.ceil(total_items / self.get_page_size(self.request))

        return Response({
            'success': True,
            'data': data,
            'meta': {
                'page': self.page.number,
                'page_size': self.get_page_size(self.request),
                'total': total_items,
                'total_pages': total_pages,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            }
        })
