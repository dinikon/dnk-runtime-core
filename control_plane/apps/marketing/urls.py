from django.urls import path

from apps.marketing.views import HomePageView

app_name = "marketing"

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
]
