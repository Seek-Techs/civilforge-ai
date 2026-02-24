from django.urls import path
from .views import analyze_boq, my_projects, project_detail

app_name = 'projects'  # ← required for namespace

urlpatterns = [
    path('', my_projects, name='my_projects'),  # empty '' because we already have /my-projects/ prefix
    path('<int:pk>/', project_detail, name='project_detail'),
    path('<int:pk>/analyze-boq/', analyze_boq, name='analyze_boq'),
]