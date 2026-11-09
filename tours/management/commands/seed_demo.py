from django.core.management.base import BaseCommand
from tours.models import Category, Tour


class Command(BaseCommand):
    help = "Создать демонстрационные категории и маршруты без пользователей и паролей"

    def handle(self, *args, **options):
        categories = {name: Category.objects.get_or_create(name=name)[0] for name in ['Конный', 'Пеший', 'Мото']}
        for title, description, price, names in [
            ('Конная прогулка в Ала-Арче', 'Горные тропы, знакомство с лошадьми и сопровождение гида.', 2500, ['Конный']),
            ('Выходные у Сон-Куля', 'Конный маршрут и пешая прогулка у высокогорного озера.', 6500, ['Конный', 'Пеший']),
            ('Мотоэкспедиция в Кегети', 'Маршрут по ущелью с остановками у водопада.', 4500, ['Мото']),
        ]:
            tour, _ = Tour.objects.get_or_create(title=title, defaults={'description': description, 'price': price})
            tour.categories.set([categories[name] for name in names])
        self.stdout.write(self.style.SUCCESS('Демонстрационные маршруты готовы'))
