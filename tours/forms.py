from django import forms
from .models import Booking, Category, Comment, Profile, Tour


class TourForm(forms.ModelForm):
    class Meta:
        model = Tour
        fields = ["title", "description", "price", "categories"]


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["phone"]


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["starts_at"]
        widgets = {"starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")}


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["text", "rating"]
