"""
HTMX utilities for handling Single Page Application (SPA) behavior.

This module provides utilities for Django views to seamlessly serve both
full HTML pages and partial HTML content based on whether the request
comes from HTMX or a regular page load.
"""


class HTMXViewMixin:
    """
    Mixin for class-based views to add HTMX context.

    This adds 'is_htmx' to the template context, allowing templates to
    conditionally extend 'base_partial.html' (content only) or 'base.html' (full page).

    Usage in view:
        class MyView(HTMXViewMixin, ListView):
            template_name = 'myapp/page.html'

    Usage in template:
        {% extends is_htmx|yesno:"base_partial.html,base.html" %}

    This way, one template file works for both HTMX and normal requests!
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_htmx'] = bool(self.request.headers.get('HX-Request'))
        return context


def is_htmx_request(request):
    """
    Helper function to detect if a request came from HTMX.

    Args:
        request: Django HttpRequest object

    Returns:
        bool: True if request has HX-Request header, False otherwise

    Usage:
        def my_view(request):
            if is_htmx_request(request):
                template = 'partial.html'
            else:
                template = 'full.html'
            return render(request, template, context)
    """
    return bool(request.headers.get('HX-Request'))
