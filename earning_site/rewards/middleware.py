from django.core.cache import cache
from django.http import HttpResponse

from .models import AuditLog
from .utils import get_client_ip


class SimpleRateLimitMiddleware:
    """Small built-in rate limiter for auth/API endpoints until Redis is enabled."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        watched = request.path.startswith(('/login/', '/register/', '/api/v1/', '/wallet/withdraw/'))
        if watched:
            ip = get_client_ip(request) or 'unknown'
            key = f"rate:{ip}:{request.path}"
            count = cache.get(key, 0) + 1
            cache.set(key, count, 60)
            if count > 80:
                return HttpResponse('Too many requests. Please try again shortly.', status=429)
        return self.get_response(request)


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated and request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            AuditLog.objects.create(
                actor=request.user,
                action=f"{request.method} {request.path}",
                target=request.resolver_match.view_name if getattr(request, 'resolver_match', None) else '',
                ip_address=get_client_ip(request),
                metadata={'status_code': response.status_code},
            )
        return response


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings

        response = self.get_response(request)
        response.setdefault('X-Content-Type-Options', 'nosniff')
        response.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        response.setdefault(
            'Content-Security-Policy',
            '; '.join([
                f"default-src {settings.CSP_DEFAULT_SRC}",
                f"script-src {settings.CSP_SCRIPT_SRC}",
                f"style-src {settings.CSP_STYLE_SRC}",
                f"font-src {settings.CSP_FONT_SRC}",
                f"img-src {settings.CSP_IMG_SRC}",
                "connect-src 'self'",
                "frame-ancestors 'self'",
            ]),
        )
        return response
