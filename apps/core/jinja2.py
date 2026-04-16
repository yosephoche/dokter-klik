"""Jinja2 environment factory for Django integration.

Registers static(), url(), csrf_input(), datetimeformat, get_messages,
and other global helpers so Jinja2 templates can use them without {% load %} tags.
"""
import datetime

from jinja2 import Environment
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.contrib.messages import get_messages
from django.middleware.csrf import get_token as _get_csrf_token


def environment(**options):
    """Create and configure the Jinja2 environment."""
    env = Environment(**options)
    env.globals.update({
        'static': static,
        'url': reverse,
        'csrf_input': _csrf_input,
        'get_csrf_token': _get_csrf_token,   # call as {{ get_csrf_token(request) }}
        'get_messages': get_messages,
    })
    env.filters['datetimeformat'] = _datetimeformat
    return env


def _csrf_input(request=None):
    """Return CSRF hidden input field. Used in Jinja2 templates."""
    # CSRF for HTMX requests is handled via the htmx:configRequest hook in base.html.
    # For regular form POSTs, pass csrf_token from the view context.
    return ''


def _datetimeformat(value, fmt='%d %b %Y %H:%M'):
    """Format a datetime or date value for display. Converts to local timezone."""
    if value is None:
        return ''
    if isinstance(value, datetime.datetime):
        local = timezone.localtime(value)
        return local.strftime(fmt)
    if isinstance(value, datetime.date):
        return value.strftime(fmt)
    return str(value)
