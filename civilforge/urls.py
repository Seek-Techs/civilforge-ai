from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views   # ← new import

urlpatterns = [
    path('admin/', admin.site.urls),
    path('my-projects/', include('projects.urls', namespace='projects')),
    # path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    # path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='projects/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/my-projects/'), name='logout'),
]