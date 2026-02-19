from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Project

@login_required
def my_projects(request):
    all_projects = Project.objects.all()
    my_projects = Project.objects.filter(owner=request.user).order_by('-created_at')
    
    return render(request, 'projects/my_projects.html', {
        'projects': my_projects,
        'all_projects_count': all_projects.count(),
        'my_projects_count': my_projects.count(),
        'current_user': request.user.username,
    })