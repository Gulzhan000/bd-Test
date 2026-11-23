from django.contrib.auth.views import LogoutView
from django.urls import path
from django.views.generic import RedirectView

from accounts.views import CaptchaLoginView, captcha_image, profile, register

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="profile"), name="home"),
    path("accounts/register/", register, name="register"),
    path("accounts/login/", CaptchaLoginView.as_view(), name="login"),
    path("accounts/login/captcha/<uuid:challenge_id>/", captcha_image, name="captcha-image"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("accounts/profile/", profile, name="profile"),
]
