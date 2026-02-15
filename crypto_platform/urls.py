"""
Main URL Configuration for crypto_platform project
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('platform_app.urls')),
]

# Error handlers
handler404 = 'platform_app.views.handler404'
handler403 = 'platform_app.views.handler403'
handler500 = 'platform_app.views.handler500'


# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = "Influxfinancetrading Admin"
admin.site.site_title = "Influxfinancetrading Admin Portal"
admin.site.index_title = "Welcome to Influxfinancetrading Administration"
