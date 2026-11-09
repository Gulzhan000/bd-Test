from django.contrib import admin
from .models import Booking, Category, Comment, Profile, Tour


@admin.register(Tour)
class TourAdmin(admin.ModelAdmin):
    list_display = ["title", "price"]
    filter_horizontal = ["categories"]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ["user", "tour", "starts_at", "attended"]
    list_filter = ["attended"]


admin.site.register([Category, Comment, Profile])
admin.site.site_header = "Ат Жол — конные туры"
