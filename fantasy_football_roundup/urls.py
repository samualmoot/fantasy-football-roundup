"""
URL configuration for fantasy_football_roundup project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from roundup.views import (
    homepage,
    weekly_report,
    weekly_report_narrative_api,
    weekly_report_overview_api,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('report/<int:year>/<int:week>/', weekly_report, name='weekly_report'),
    path('report/<int:year>/<int:week>/narrative.json', weekly_report_narrative_api, name='weekly_report_narrative_api'),
    path('report/<int:year>/<int:week>/overview.json', weekly_report_overview_api, name='weekly_report_overview_api'),

        # Homepage redirect
    path('', homepage, name='homepage'),
]
