from django.conf import settings

def system_info(request):
    return {
        "APP_NAME": getattr(settings, "APP_NAME", "SADACO Management System"),
        "APP_VERSION": getattr(settings, "APP_VERSION", ""),
    }
