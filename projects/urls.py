from django.urls import path
from .views import my_projects

app_name = 'projects'  # ← required for namespace

urlpatterns = [
    path('', my_projects, name='my_projects'),  # empty '' because we already have /my-projects/ prefix
]