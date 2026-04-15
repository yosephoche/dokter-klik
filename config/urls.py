"""Root URL configuration for DokterKlik."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # Auth
    path('api/auth/', include('apps.accounts.urls')),
    # API endpoints
    path('api/patients/', include('apps.patients.urls')),
    path('api/visits/', include('apps.emr.urls')),
    path('api/icd10/', include('apps.emr.icd_urls')),
    path('api/queue/', include('apps.queue.api_urls')),
    path('api/invoices/', include('apps.billing.urls')),
    path('api/payments/', include('apps.billing.payment_urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/satusehat/', include('apps.satusehat.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
    # WhatsApp webhook
    path('webhooks/whatsapp/', include('apps.whatsapp.urls')),
    # HTMX / browser views
    path('queue/', include('apps.queue.urls')),
    path('clinics/', include('apps.clinics.urls')),
    path('', include('apps.dashboard.web_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
