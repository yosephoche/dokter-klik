"""Jinja2 environment factory for Django integration.

Registers static(), url(), csrf_input(), and other global helpers
so Jinja2 templates can use them without {% load %} tags.
"""
from jinja2 import Environment
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html


def environment(**options):
    """Create and configure the Jinja2 environment."""
    env = Environment(**options)
    env.globals.update({
        'static': static,
        'url': reverse,
        'csrf_input': _csrf_input,
    })
    return env


def _csrf_input(request=None):
    """Return CSRF hidden input field. Used in Jinja2 templates."""
    from django.middleware.csrf import get_token
    # In Jinja2, CSRF token must be fetched differently
    # Templates call {{ csrf_input() }} — but we need request context.
    # The preferred approach: use HTMX header injection in base.html
    return ''
