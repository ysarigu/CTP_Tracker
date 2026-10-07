from django.urls import path

from . import views


app_name = "tracker"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("work/", views.log_work, name="log_work"),
    path("sections/<str:section_id>/complete/", views.mark_section_test, name="mark_section_test"),
    path("email-settings/", views.email_settings, name="email_settings"),
    path("email/draft/", views.download_email_draft, name="email_draft"),
    path("email/mark-sent/", views.mark_email_sent, name="mark_email_sent"),
]
