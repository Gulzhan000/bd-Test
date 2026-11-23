# Тестирование пользователей в Django

Практическая работа находится в папке `users-testing` репозитория `bd-Test`. Здесь отдельные настройки и база SQLite. Приложение `accounts` реализует регистрацию, вход с капчей, личный кабинет и выход.

## Запуск

Из корня репозитория:

```sh
cd users-testing
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Откройте http://127.0.0.1:8000/accounts/register/. Зарегистрируйтесь и на странице входа введите имя, пароль и пять цифр с картинки. При неверном коде сервер выдаёт новую картинку. После входа откроется личный кабинет.

Капча предназначена для локальной учебной демонстрации. Код действует пять минут, относится к текущему сеансу и удаляется после первой отправки. Для тестов ожидаемый код берётся из отдельной тестовой базы Django.

## Запуск тестов и отчёт

```sh
python manage.py test accounts -v 2
python manage.py test_users_report -v 2
python manage.py check
```

Первая команда запускает тесты. Вторая запускает их заново и сохраняет статусы всех сценариев в [Word-отчёт](reports/users-test-report.docx). Если тест завершится ошибкой, команда сохранит отчёт с деталями ошибки и вернёт ненулевой код завершения. Путь можно изменить через `--output`.

Если к отчёту нужно приложить сделанные вручную снимки браузера, передайте папку через `--screenshots` с файлами `01-register.jpg`, `02-captcha-error.jpg` и `03-profile.jpg`.

## Материалы

- [Пример django-test](https://github.com/narmuhamedov/TestingPO/tree/master/django-test)
- [Видео «test users»](https://youtu.be/eUOtRNewDfY)
