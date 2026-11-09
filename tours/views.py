from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from .forms import BookingForm, CategoryForm, CommentForm, ProfileForm, TourForm
from .models import Booking, Comment, Profile, Tour


@require_http_methods(["GET"])
def tour_list(request):
    """Каталог маршрутов с категориями. Шаблон tours/list.html."""
    return render(request, "tours/list.html", {"tours": Tour.objects.prefetch_related("categories")})


@require_http_methods(["GET"])
def tour_detail(request, pk):
    """Описание тура, отзывы и ссылки на покупку. Шаблон tours/detail.html."""
    return render(request, "tours/detail.html", {"tour": get_object_or_404(Tour, pk=pk)})


def save_form(request, form, title, destination="tour_list"):
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except IntegrityError:
            form.add_error(None, "Такая запись уже существует. Проверьте дату и время.")
        else:
            return redirect(destination)
    return render(request, "tours/form.html", {"form": form, "title": title})


@login_required
@require_http_methods(["GET", "POST"])
def book(request, pk):
    """Покупка от имени текущего клиента. Проверяет время и уникальность покупки."""
    tour = get_object_or_404(Tour, pk=pk)
    form = BookingForm(request.POST or None, instance=Booking(user=request.user, tour=tour))
    return save_form(request, form, "Купить тур «" + tour.title + "»")


@login_required
@require_http_methods(["GET", "POST"])
def comment(request, pk):
    """Отзыв текущего клиента. Требуется подтверждённое прошлое посещение."""
    tour = get_object_or_404(Tour, pk=pk)
    form = CommentForm(request.POST or None, instance=Comment(user=request.user, tour=tour))
    return save_form(request, form, "Оставить комментарий")


@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    """Создание или изменение единственного профиля текущего клиента."""
    instance = Profile.objects.filter(user=request.user).first() or Profile(user=request.user)
    return save_form(request, ProfileForm(request.POST or None, instance=instance), "Контактные данные")


@user_passes_test(lambda user: user.is_staff)
@require_http_methods(["GET", "POST"])
def tour_create(request):
    """Добавление тура сотрудником с сохранением категорий многие ко многим."""
    return save_form(request, TourForm(request.POST or None), "Новый тур")


@user_passes_test(lambda user: user.is_staff)
@require_http_methods(["GET", "POST"])
def category_create(request):
    """Добавление уникальной категории сотрудником."""
    return save_form(request, CategoryForm(request.POST or None), "Новая категория")
