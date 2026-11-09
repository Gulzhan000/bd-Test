from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from .models import Booking, Category, Comment, Profile, Tour


class TourTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('gulzhan', password='test-password')
        self.other = get_user_model().objects.create_user('other')
        self.staff = get_user_model().objects.create_superuser('guide', password='test-password')
        self.category = Category.objects.create(name='Конный')
        self.tour = Tour.objects.create(title='Ала-Арча', description='Прогулка в горах', price=2500)
        self.tour.categories.add(self.category)
        self.second = Tour.objects.create(title='Сон-Куль', description='Поездка к озеру', price=5000)
        self.future = timezone.now() + timedelta(days=5)
        self.payload = {'starts_at': timezone.localtime(self.future).strftime('%Y-%m-%dT%H:%M')}
        self.client.force_login(self.user)

    def visited(self, **kwargs):
        return Booking.objects.create(user=self.user, tour=self.tour, starts_at=timezone.now()-timedelta(days=2), attended=True, **kwargs)

    def test_one_profile_per_user_database(self):
        Profile.objects.create(user=self.user, phone='0555123456')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Profile.objects.create(user=self.user, phone='0777123456')

    def test_many_categories_and_many_tours(self):
        hiking = Category.objects.create(name='Пеший')
        self.tour.categories.add(hiking)
        self.second.categories.add(self.category)
        self.assertEqual(self.tour.categories.count(), 2)
        self.assertEqual(self.category.tours.count(), 2)
        self.tour.categories.remove(hiking)
        self.assertTrue(Category.objects.filter(pk=hiking.pk).exists())

    def test_duplicate_booking_database(self):
        Booking.objects.create(user=self.user, tour=self.tour, starts_at=self.future)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Booking.objects.create(user=self.user, tour=self.second, starts_at=self.future)

    def test_different_times_allowed(self):
        for hour in (0, 1):
            Booking.objects.create(user=self.user, tour=self.tour, starts_at=self.future+timedelta(hours=hour))
        self.assertEqual(self.user.bookings.count(), 2)

    def test_different_users_same_time_allowed(self):
        for user in (self.user, self.other):
            Booking.objects.create(user=user, tour=self.tour, starts_at=self.future)
        self.assertEqual(self.tour.bookings.count(), 2)

    def test_booking_post(self):
        response = self.client.post(reverse('book', args=[self.tour.pk]), self.payload)
        self.assertRedirects(response, '/')
        booking = Booking.objects.get()
        self.assertEqual(booking.user, self.user)
        self.assertEqual(booking.tour, self.tour)
        self.assertFalse(booking.attended)

    def test_duplicate_booking_post(self):
        self.client.post(reverse('book', args=[self.tour.pk]), self.payload)
        response = self.client.post(reverse('book', args=[self.second.pk]), self.payload)
        self.assertTrue(response.context['form'].errors)
        self.assertEqual(Booking.objects.count(), 1)

    def test_booking_invalid_dates(self):
        for value in ('', 'invalid', '2020-01-01T10:00'):
            with self.subTest(value=value):
                response = self.client.post(reverse('book', args=[self.tour.pk]), {'starts_at': value})
                self.assertTrue(response.context['form'].errors)
        self.assertEqual(Booking.objects.count(), 0)

    def test_booking_ignores_forged_identity_and_attendance(self):
        self.client.post(reverse('book', args=[self.tour.pk]), {**self.payload, 'user': self.other.pk, 'tour': self.second.pk, 'attended': True})
        b = Booking.objects.get()
        self.assertEqual((b.user, b.tour, b.attended), (self.user, self.tour, False))

    def test_future_attendance_rejected(self):
        with self.assertRaises(ValidationError):
            Booking(user=self.user, tour=self.tour, starts_at=self.future, attended=True).full_clean()

    def test_multiple_comments_allowed(self):
        self.visited()
        for text in ('Отличный тур', 'Спасибо гиду'):
            self.assertRedirects(self.client.post(reverse('comment', args=[self.tour.pk]), {'text': text, 'rating': 5}), '/')
        self.assertEqual(self.user.comments.count(), 2)
        self.assertEqual(self.tour.comments.count(), 2)

    def test_comment_without_booking_rejected(self):
        r = self.client.post(reverse('comment', args=[self.tour.pk]), {'text': 'Отзыв', 'rating': 5})
        self.assertTrue(r.context['form'].errors)
        self.assertFalse(Comment.objects.exists())

    def test_unconfirmed_visit_rejected(self):
        b = self.visited()
        b.attended = False
        b.save()
        self.test_comment_without_booking_rejected()

    def test_future_visit_rejected(self):
        Booking.objects.create(user=self.user, tour=self.tour, starts_at=self.future, attended=True)
        self.test_comment_without_booking_rejected()

    def test_other_users_visit_rejected(self):
        b = self.visited()
        b.user = self.other
        b.save()
        self.test_comment_without_booking_rejected()

    def test_other_tour_visit_rejected(self):
        b = self.visited()
        b.tour = self.second
        b.save()
        self.test_comment_without_booking_rejected()

    def test_invalid_comment_fields(self):
        self.visited()
        for data in ({'text': '', 'rating': 5}, {'text': '   ', 'rating': 5}, {'text': 'x'*2001, 'rating': 5}, {'text': 'OK', 'rating': 0}, {'text': 'OK', 'rating': 6}, {'text': 'OK', 'rating': 'abc'}, {'text': 'OK'}):
            with self.subTest(data=str(data)[:80]):
                r = self.client.post(reverse('comment', args=[self.tour.pk]), data)
                self.assertTrue(r.context['form'].errors)
        self.assertFalse(Comment.objects.exists())

    def test_comment_rating_boundaries(self):
        self.visited()
        for rating in (1, 5):
            self.assertRedirects(self.client.post(reverse('comment', args=[self.tour.pk]), {'text': 'Тур', 'rating': rating}), '/')

    def test_comment_cannot_forge_user_or_tour(self):
        self.visited()
        self.client.post(reverse('comment', args=[self.tour.pk]), {'text': 'Спасибо', 'rating': 5, 'user': self.other.pk, 'tour': self.second.pk})
        c = Comment.objects.get()
        self.assertEqual((c.user, c.tour), (self.user, self.tour))

    def test_rating_constraint_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Comment.objects.create(user=self.user, tour=self.tour, text='Тур', rating=6)

    def test_profile_create_and_update(self):
        for phone in ('0555123456', '0777123456'):
            self.assertRedirects(self.client.post('/profile/', {'phone': phone}), '/')
        self.assertEqual(Profile.objects.count(), 1)
        self.assertEqual(self.user.profile.phone, '0777123456')

    def test_invalid_profile(self):
        for phone in ('', 'x'*31):
            r = self.client.post('/profile/', {'phone': phone})
            self.assertTrue(r.context['form'].errors)
        self.assertFalse(Profile.objects.exists())

    def test_profile_cannot_modify_another_user(self):
        self.client.post('/profile/', {'phone': '0555123456', 'user': self.other.pk})
        self.assertEqual(Profile.objects.get().user, self.user)

    def test_staff_create_tour_with_categories(self):
        self.client.force_login(self.staff)
        r = self.client.post('/tours/new/', {'title': 'Кегети', 'description': 'Конная прогулка', 'price': '3000.50', 'categories': [self.category.pk]})
        self.assertRedirects(r, '/')
        self.assertEqual(Tour.objects.get(title='Кегети').categories.get(), self.category)

    def test_invalid_tour_fields(self):
        self.client.force_login(self.staff)
        data = {'title': 'Тур', 'description': 'Описание', 'price': '1000', 'categories': [self.category.pk]}
        for field, value in [('title', ''), ('title', 'x'*161), ('description', ''), ('price', '-1'), ('price', 'abc'), ('price', '1.001'), ('categories', []), ('categories', [9999])]:
            with self.subTest(field=field, value=value):
                r = self.client.post('/tours/new/', {**data, field: value})
                self.assertTrue(r.context['form'].errors)
        self.assertEqual(Tour.objects.count(), 2)

    def test_price_constraint_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Tour.objects.create(title='Тур', description='Тур', price=-1)

    def test_staff_create_category(self):
        self.client.force_login(self.staff)
        self.assertRedirects(self.client.post('/categories/new/', {'name': 'Мото'}), '/')
        self.assertTrue(Category.objects.filter(name='Мото').exists())

    def test_invalid_category(self):
        self.client.force_login(self.staff)
        for name in ('', 'x'*81, 'Конный'):
            r = self.client.post('/categories/new/', {'name': name})
            self.assertTrue(r.context['form'].errors)
        self.assertEqual(Category.objects.count(), 1)

    def test_client_cannot_create_tours_or_categories(self):
        for url in ('/tours/new/', '/categories/new/'):
            self.assertEqual(self.client.post(url, {'name': 'Мото'}).status_code, 302)
        self.assertEqual(Tour.objects.count(), 2)
        self.assertEqual(Category.objects.count(), 1)

    def test_anonymous_cannot_submit(self):
        self.client.logout()
        for url in ('/profile/', '/tours/new/', '/categories/new/', reverse('book', args=[self.tour.pk]), reverse('comment', args=[self.tour.pk])):
            r = self.client.post(url, {})
            self.assertEqual(r.status_code, 302)
            self.assertIn('/accounts/login/', r.url)
        self.assertFalse(Booking.objects.exists())
        self.assertFalse(Comment.objects.exists())

    def test_csrf_all_forms(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.staff)
        for url in ('/profile/', '/tours/new/', '/categories/new/', reverse('book', args=[self.tour.pk]), reverse('comment', args=[self.tour.pk])):
            self.assertEqual(client.post(url, {}).status_code, 403)

    def test_valid_csrf_submission(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        client.get('/profile/')
        self.assertRedirects(client.post('/profile/', {'phone': '0555123456', 'csrfmiddlewaretoken': client.cookies['csrftoken'].value}), '/')

    def test_unsupported_methods(self):
        self.client.force_login(self.staff)
        for url in ('/', '/profile/', '/tours/new/', '/categories/new/', reverse('book', args=[self.tour.pk]), reverse('comment', args=[self.tour.pk])):
            self.assertEqual(self.client.put(url).status_code, 405)

    def test_get_forms_does_not_create_records(self):
        self.client.force_login(self.staff)
        for url in ('/profile/', '/tours/new/', '/categories/new/', reverse('book', args=[self.tour.pk]), reverse('comment', args=[self.tour.pk])):
            self.assertEqual(self.client.get(url).status_code, 200)
        self.assertFalse(Booking.objects.exists())
        self.assertFalse(Comment.objects.exists())
        self.assertFalse(Profile.objects.exists())
        self.assertEqual(Tour.objects.count(), 2)

    def test_missing_tour(self):
        for name in ('tour_detail', 'book', 'comment'):
            self.assertEqual(self.client.get(reverse(name, args=[99999])).status_code, 404)
        for name in ('book', 'comment'):
            self.assertEqual(self.client.post(reverse(name, args=[99999]), {}).status_code, 404)

    def test_catalog_and_detail(self):
        self.assertContains(self.client.get('/'), 'Ала-Арча')
        self.assertContains(self.client.get('/'), 'Конный')
        self.assertContains(self.client.get(reverse('tour_detail', args=[self.tour.pk])), 'Прогулка в горах')

    def test_html_is_escaped(self):
        self.tour.title = '<script>alert(1)</script>'
        self.tour.save()
        self.assertContains(self.client.get('/'), '&lt;script&gt;')
        self.assertNotContains(self.client.get('/'), self.tour.title)

    def test_admindocs_requires_staff(self):
        r = self.client.get('/admin/doc/')
        self.assertEqual(r.status_code, 302)

    def test_admindocs_models_and_views(self):
        self.client.force_login(self.staff)
        for url in ('/admin/doc/', '/admin/doc/models/', '/admin/doc/models/tours.booking/', '/admin/doc/models/tours.comment/', '/admin/doc/views/', '/admin/doc/views/tours.views.book/'):
            self.assertEqual(self.client.get(url).status_code, 200)
        self.assertContains(self.client.get('/admin/doc/models/tours.booking/'), 'Покупка тура')

    def test_empty_catalog(self):
        Tour.objects.all().delete()
        self.assertContains(self.client.get('/'), 'Туры пока не добавлены.')
