from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    """Один профиль на одного пользователя. Контактные данные участника."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField("Телефон", max_length=30)

    def __str__(self):
        return self.user.get_username()


class Category(models.Model):
    """Категория маршрутов: конный, пеший или мото."""

    name = models.CharField("Название", max_length=80, unique=True)

    def __str__(self):
        return self.name


class Tour(models.Model):
    """Маршрут стартапа. Один тур может входить в несколько категорий."""

    title = models.CharField("Название", max_length=160)
    description = models.TextField("Описание")
    price = models.DecimalField("Цена в сомах", max_digits=9, decimal_places=2, validators=[MinValueValidator(0)])
    categories = models.ManyToManyField(Category, related_name="tours", verbose_name="Категории")

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(price__gte=0), name="tour_price_nonnegative")]

    def __str__(self):
        return self.title


class Booking(models.Model):
    """Покупка тура. Пользователь может купить только один тур на одно время начала."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    tour = models.ForeignKey(Tour, on_delete=models.PROTECT, related_name="bookings")
    starts_at = models.DateTimeField("Дата и время начала", help_text="Местное время Бишкека")
    attended = models.BooleanField("Посещение подтверждено", default=False, help_text="Отмечается сотрудником после завершения тура")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "starts_at"], name="one_tour_per_person_and_time", violation_error_message="На это время у вас уже есть тур.")]

    def clean(self):
        if self.starts_at and self.starts_at <= timezone.now() and not self.pk:
            raise ValidationError({"starts_at": "Выберите будущее время."})
        if self.attended and self.starts_at and self.starts_at > timezone.now():
            raise ValidationError({"attended": "Будущий тур нельзя отметить посещённым."})

    def __str__(self):
        return f"{self.user} — {self.tour} — {self.starts_at}"


class Comment(models.Model):
    """Несколько отзывов клиента о турах с подтверждённым посещением."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name="comments")
    text = models.TextField("Комментарий", max_length=2000)
    rating = models.PositiveSmallIntegerField("Оценка", validators=[MinValueValidator(1), MaxValueValidator(5)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name="comment_rating_range")]

    def clean(self):
        if self.user_id and self.tour_id and not Booking.objects.filter(user_id=self.user_id, tour_id=self.tour_id, attended=True, starts_at__lte=timezone.now()).exists():
            raise ValidationError("Комментарий доступен только после подтверждённого посещения тура.")

    def __str__(self):
        return f"{self.user}: {self.rating}"
