import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crypto_platform.settings')

application = get_wsgi_application()

# Vercel expects 'app' variable
app = application