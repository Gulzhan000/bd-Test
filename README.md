# Ат Жол

Учебный стартап для покупки конных и других туров по Кыргызстану.
Python 3.10+, Django 5.2.19, SQLite.

## Запуск в VS Code

Открыть эту папку в VS Code. В терминале:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver
```

Каталог: http://127.0.0.1:8000/
Админка: http://127.0.0.1:8000/admin/
Документация Django admindocs: http://127.0.0.1:8000/admin/doc/

Клиентов создаёт сотрудник в админке (Users). Клиент входит через «Войти», заполняет профиль и покупает тур, выбирая дату и время. Сотрудник отмечает attended в разделе Booking после фактического посещения. После этого клиент может оставить несколько отзывов. Добавление туров и категорий доступно сотруднику.

## Связи и правила

- User — Profile: OneToOneField.
- User — Booking, Tour — Booking, User — Comment, Tour — Comment: ForeignKey.
- Tour — Category: ManyToManyField.
- UNIQUE(user, starts_at) запрещает одному клиенту покупать любые два тура с одинаковым временем начала, в том числе повторно тот же тур. В другое время покупка разрешена.
- Время вводится в часовом поясе Asia/Bishkek, сохраняется с поддержкой timezone.
- Комментарии доступны после прошлого посещения с отметкой сотрудника. Ограничения проверяются ModelForm и clean модели. Прямые objects.create/bulk_create не запускают clean: записи посещения и комментариев через ORM требуют full_clean. SQL гарантирует уникальность покупок, диапазон оценки и неотрицательную цену.
- Покупка здесь означает запись бронирования, платёжный шлюз не подключён. Длительность туров и пересечение интервалов не моделируются: условие относится к точному времени начала.

## Тестирование

```sh
python manage.py test tours -v 2
python manage.py check
python manage.py makemigrations --check --dry-run
```

40 тестов: все формы отправки, права, CSRF, подмена пользователя, ограничения SQL, связи, admindocs. ReportingRunner записывает фактические результаты в reports/test-results.json. Текстовый журнал последнего полного запуска: reports/test-results.txt. Для его обновления:

```sh
python manage.py test tours -v 2 > reports/test-results.txt 2>&1
```

Настройки предназначены для локального учебного запуска. Для развёртывания задайте DJANGO_SECRET_KEY, DJANGO_DEBUG=0 и собственный ALLOWED_HOSTS, настройте HTTPS и статические файлы.

## Учебные материалы

- https://github.com/narmuhamedov/TestingPO/tree/master/django-test — изучены модели в otnosheniye, ModelForm и тесты Client/TestCase; новый проект реализован отдельно.
- https://youtu.be/gAygHlilgGI — страница «test database» доступна, автоматические субтитры получить не удалось; содержание видео не выдаётся за изученное.
- https://docs.djangoproject.com/en/5.2/ref/contrib/admin/admindocs/
- https://docs.djangoproject.com/en/5.2/ref/models/constraints/
