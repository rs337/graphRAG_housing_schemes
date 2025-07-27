"""
URL Configuration for Chat App
This module defines the URL patterns for the GraphRAG chat application.
"""

from django.urls import path
from . import views

# App name for namespace (allows reverse URL lookups like 'chat:index')
app_name = 'chat'

urlpatterns = [
    # Main chat interface page
    path('', views.index, name='index'),
    
    # AJAX endpoint for processing chat queries
    path('query/', views.ChatQueryView.as_view(), name='query'),
    
    # Health check endpoint
    path('health/', views.health_check, name='health'),
] 