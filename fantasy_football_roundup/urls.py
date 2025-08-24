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
    weekly_report,
    weekly_report_narrative_api,
    weekly_report_overview_api,
    weekly_report_scoreboard_api,
    weekly_report_standings_api,
    weekly_report_booms_busts_api,
    weekly_report_awards_api,
    weekly_report_export_pdf,
    team_logo,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('report/<int:year>/<int:week>/', weekly_report, name='weekly_report'),
    path('report/<int:year>/<int:week>/narrative.json', weekly_report_narrative_api, name='weekly_report_narrative_api'),
    path('report/<int:year>/<int:week>/overview.json', weekly_report_overview_api, name='weekly_report_overview_api'),
    # Component APIs for progressive loading
    path('report/<int:year>/<int:week>/scoreboard.json', weekly_report_scoreboard_api, name='weekly_report_scoreboard_api'),
    path('report/<int:year>/<int:week>/standings.json', weekly_report_standings_api, name='weekly_report_standings_api'),
    path('report/<int:year>/<int:week>/booms-busts.json', weekly_report_booms_busts_api, name='weekly_report_booms_busts_api'),
    path('report/<int:year>/<int:week>/awards.json', weekly_report_awards_api, name='weekly_report_awards_api'),

    # Export PDF
    path('report/<int:year>/<int:week>/export.pdf', weekly_report_export_pdf, name='weekly_report_export_pdf'),

    # New homepage: Week 1 report
    path('', lambda request: weekly_report(request, year=2025, week=1), name='homepage'),

    # Disable draft analysis: route to week 1 report
    path('draft/', lambda request: weekly_report(request, year=2025, week=1), name='draft_analysis'),

    path('assets/team-logo/<int:team_id>.png', team_logo, name='team_logo'),
]
