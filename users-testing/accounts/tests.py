from datetime import timedelta

from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import LoginChallenge

User = get_user_model()
USERNAME = "student_demo"
EMAIL = "student@example.com"
PASSWORD = "Demo-study-9532!"


class RegistrationTests(TestCase):
    def setUp(self):
        self.url = reverse("register")
        self.payload = {
            "username": USERNAME,
            "email": EMAIL,
            "password1": PASSWORD,
            "password2": PASSWORD,
        }

    def test_registration_page(self):
        """Форма регистрации открывается и показывает обязательные поля."""
        response = self.client.get(self.url)
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="password2"')

    def test_registration_saves_user_and_hash(self):
        """Корректные данные создают пользователя. Пароль хранится как хеш."""
        self.assertRedirects(self.client.post(self.url, self.payload), reverse("login"), fetch_redirect_response=False)
        user = User.objects.get(username=USERNAME)
        self.assertEqual(user.email, EMAIL)
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_duplicate_username(self):
        """Занятое имя не создаёт дубликат пользователя."""
        User.objects.create_user(username=USERNAME, password=PASSWORD)
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.context["form"].errors.as_data()["username"][0].code, "unique")
        self.assertEqual(User.objects.count(), 1)

    def test_password_mismatch(self):
        """При разных паролях пользователь не создаётся."""
        response = self.client.post(self.url, {**self.payload, "password2": "Another-234"})
        self.assertEqual(response.context["form"].errors.as_data()["password2"][0].code, "password_mismatch")
        self.assertFalse(User.objects.exists())

    def test_invalid_email(self):
        """Неверный формат электронной почты отклоняется."""
        response = self.client.post(self.url, {**self.payload, "email": "wrong"})
        self.assertIn("email", response.context["form"].errors)
        self.assertFalse(User.objects.exists())


class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username=USERNAME, email=EMAIL, password=PASSWORD)

    def setUp(self):
        self.url = reverse("login")
        self.credentials = {"username": USERNAME, "password": PASSWORD}

    def challenge(self, client=None):
        client = self.client if client is None else client
        response = client.get(self.url)
        challenge = LoginChallenge.objects.get(pk=response.context["challenge_id"])
        return challenge, {"captcha_id": challenge.pk, "captcha": challenge.code}

    def assert_rejected(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertIn("captcha", response.context["form"].errors)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_correct_credentials_and_captcha(self):
        """Верные пароль и капча открывают личный кабинет через сеанс Django."""
        item, captcha = self.challenge()
        response = self.client.post(self.url, {**self.credentials, **captcha})
        self.assertRedirects(response, reverse("profile"))
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
        self.assertFalse(LoginChallenge.objects.filter(pk=item.pk).exists())

    def test_captcha_image(self):
        """Форма подставляет изображение капчи из текущего сеанса."""
        page = self.client.get(self.url)
        image_url = reverse("captcha-image", args=[page.context["challenge_id"]])
        self.assertContains(page, image_url)
        response = self.client.get(image_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertTrue(response.content.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(Client().get(image_url).status_code, 404)

    def test_missing_captcha(self):
        """Пустой код капчи отклоняется даже при верном пароле."""
        item, _ = self.challenge()
        response = self.client.post(self.url, {**self.credentials, "captcha_id": item.pk})
        self.assert_rejected(response)
        self.assertNotEqual(response.context["challenge_id"], item.pk)

    def test_wrong_captcha(self):
        """Неверный код капчи блокирует вход и выдаёт новую картинку."""
        item, captcha = self.challenge()
        response = self.client.post(self.url, {**self.credentials, **captcha, "captcha": "00000"})
        self.assert_rejected(response)
        self.assertNotEqual(response.context["challenge_id"], item.pk)
        self.assertFalse(LoginChallenge.objects.filter(pk=item.pk).exists())

    def test_wrong_password_with_correct_captcha(self):
        """Правильная капча не позволяет войти с неверным паролем."""
        item, captcha = self.challenge()
        response = self.client.post(self.url, {**self.credentials, **captcha, "password": "wrong"})
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertNotIn("captcha", response.context["form"].errors)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertFalse(LoginChallenge.objects.filter(pk=item.pk).exists())

    def test_missing_challenge_id(self):
        """Вход без идентификатора выданной капчи отклоняется."""
        self.assert_rejected(self.client.post(self.url, {**self.credentials, "captcha": "22222"}))

    def test_expired_captcha(self):
        """Код с истёкшим сроком действия отклоняется."""
        item, captcha = self.challenge()
        LoginChallenge.objects.filter(pk=item.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assert_rejected(self.client.post(self.url, {**self.credentials, **captcha}))

    def test_other_session_captcha(self):
        """Код из другого сеанса нельзя использовать для входа."""
        item, captcha = self.challenge(Client())
        self.assert_rejected(self.client.post(self.url, {**self.credentials, **captcha}))
        self.assertTrue(LoginChallenge.objects.filter(pk=item.pk).exists())

    def test_replayed_captcha(self):
        """Использованный код отклоняется при повторной отправке."""
        _, captcha = self.challenge()
        self.client.post(self.url, {**self.credentials, **captcha, "password": "wrong"})
        self.assert_rejected(self.client.post(self.url, {**self.credentials, **captcha}))


class ProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username=USERNAME, email=EMAIL, password=PASSWORD)

    def test_anonymous_user_redirected_to_login(self):
        """Гость перенаправляется со страницы кабинета на вход."""
        profile_url = reverse("profile")
        self.assertRedirects(
            self.client.get(profile_url),
            f"{reverse('login')}?next={profile_url}",
            fetch_redirect_response=False,
        )

    def test_profile_displays_current_user_only(self):
        """Кабинет показывает имя и почту текущего пользователя."""
        other = User.objects.create_user(username="other", email="other@example.com")
        self.client.force_login(self.user)
        response = self.client.get(reverse("profile"), {"user": other.pk})
        self.assertContains(response, USERNAME)
        self.assertContains(response, EMAIL)
        self.assertNotContains(response, other.email)

    def test_registration_login_and_profile(self):
        """Новый пользователь проходит регистрацию, вход с капчей и открывает кабинет."""
        registration = {
            "username": "new_student",
            "email": "new-student@example.com",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }
        login_url = reverse("login")
        response = self.client.post(reverse("register"), registration, follow=True)
        self.assertRedirects(response, login_url)
        challenge = LoginChallenge.objects.get(pk=response.context["challenge_id"])
        response = self.client.post(login_url, {
            "username": registration["username"],
            "password": PASSWORD,
            "captcha_id": challenge.pk,
            "captcha": challenge.code,
        }, follow=True)
        self.assertRedirects(response, reverse("profile"))
        self.assertContains(response, registration["email"])

    def test_logout_closes_profile_access(self):
        """После выхода из сеанса кабинет снова требует входа."""
        self.client.force_login(self.user)
        self.assertRedirects(
            self.client.post(reverse("logout")), reverse("login"), fetch_redirect_response=False
        )
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertEqual(self.client.get(reverse("profile")).status_code, 302)
