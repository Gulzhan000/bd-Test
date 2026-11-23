from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from .captcha import draw_challenge, new_challenge
from .forms import CaptchaLoginForm, RegistrationForm
from .models import LoginChallenge


class CaptchaLoginView(LoginView):
    authentication_form = CaptchaLoginForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["challenge_id"] = new_challenge(self.request).pk
        return context


def register(request):
    form = RegistrationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("login")
    return render(request, "accounts/register.html", {"form": form})


@login_required
@never_cache
def profile(request):
    return render(request, "accounts/profile.html")


@require_safe
@never_cache
def captcha_image(request, challenge_id):
    challenge = get_object_or_404(
        LoginChallenge,
        pk=challenge_id,
        session_key=request.session.session_key,
        expires_at__gt=timezone.now(),
    )
    return HttpResponse(draw_challenge(challenge.code), content_type="image/png")
