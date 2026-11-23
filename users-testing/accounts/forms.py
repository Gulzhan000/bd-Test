from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .captcha import check_challenge


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(label="Электронная почта")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")


class CaptchaLoginForm(AuthenticationForm):
    captcha_id = forms.UUIDField(widget=forms.HiddenInput, required=False)
    captcha = forms.CharField(
        label="Код с картинки",
        required=False,
        max_length=16,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
    )

    def clean(self):
        challenge_id = self.cleaned_data.get("captcha_id")
        answer = self.cleaned_data.get("captcha", "")
        valid = challenge_id and check_challenge(self.request, challenge_id, answer)
        if not valid:
            message = (
                "Введите код с картинки." if not answer
                else "Код неверен или устарел. Введите новый код."
            )
            self.add_error("captcha", message)
            return self.cleaned_data
        return super().clean()
