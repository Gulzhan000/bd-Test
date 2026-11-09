from django.urls import path
from . import views

urlpatterns = [
    path("", views.tour_list, name="tour_list"),
    path("tours/new/", views.tour_create, name="tour_create"),
    path("categories/new/", views.category_create, name="category_create"),
    path("profile/", views.profile, name="profile"),
    path("tours/<int:pk>/", views.tour_detail, name="tour_detail"),
    path("tours/<int:pk>/book/", views.book, name="book"),
    path("tours/<int:pk>/comment/", views.comment, name="comment"),
]
