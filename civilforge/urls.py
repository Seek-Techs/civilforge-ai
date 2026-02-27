"""
civilforge/urls.py  — the master URL file.

Think of URLs like a post office sorting system.
A request comes in → Django reads the URL → routes it to the right view.

CONCEPT: include()
  Instead of listing every URL in one giant file, we split them across apps.
  include('projects.urls') means "go look in projects/urls.py for the rest".
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Django admin panel — keep this, it's useful for managing data
    path('admin/', admin.site.urls),

    # allauth handles ALL auth URLs:
    # /accounts/login/         — sign in
    # /accounts/logout/        — sign out
    # /accounts/signup/        — register
    # /accounts/email/         — manage email addresses
    # /accounts/password/...   — change/reset password
    # /accounts/confirm-email/ — verify email after registration
    path('accounts/', include('allauth.urls')),

    # Our projects app
    path('my-projects/', include('projects.urls', namespace='projects')),
]
