from django.utils.functional import SimpleLazyObject

from .models import PlatformSettings


def platform_settings(request):
    """Expose Admin > Settings (min deposit/withdrawal, fees) to every template,
    so public pages can't drift from what the admin actually configured.
    Lazy, so pages that never mention it don't pay for the query."""
    return {'platform_settings': SimpleLazyObject(lambda: PlatformSettings.objects.first() or PlatformSettings())}
