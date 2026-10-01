from django.contrib import admin
from .models import ProductionJob, ProductionProgress, ProductionMaterial, ProductionIssue
admin.site.register([ProductionJob,ProductionProgress,ProductionMaterial,ProductionIssue])
