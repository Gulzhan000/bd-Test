from collections import Counter
from io import StringIO
from pathlib import Path
from unittest import TextTestResult, TextTestRunner

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test.runner import DiscoverRunner

from accounts.report import write_docx


class ReportResult(TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def record(self, test, status, details=""):
        self.records.append((test.id(), test.shortDescription() or test.id(), status, details))

    def addSuccess(self, test):
        super().addSuccess(test)
        self.record(test, "PASS")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.record(test, "FAIL", self.failures[-1][1])

    def addError(self, test, err):
        super().addError(test, err)
        self.record(test, "ERROR", self.errors[-1][1])

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.record(test, "SKIP", reason)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.record(test, "XFAIL", self.expectedFailures[-1][1])

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.record(test, "XPASS")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.record(subtest, "FAIL" if issubclass(err[0], test.failureException) else "ERROR")


class ReportRunner(DiscoverRunner):
    def run_suite(self, suite, **kwargs):
        self.log_stream = StringIO()
        runner = TextTestRunner(stream=self.log_stream, verbosity=self.verbosity, resultclass=ReportResult)
        self.result = runner.run(suite)
        return self.result


class Command(BaseCommand):
    help = "Запускает тесты аккаунтов и сохраняет фактические результаты в Word."

    def add_arguments(self, parser):
        parser.add_argument("--output", type=Path, default=settings.BASE_DIR / "reports/users-test-report.docx")
        parser.add_argument("--screenshots", type=Path, help="Папка со снимками страниц Django в формате JPEG.")

    def handle(self, *args, **options):
        runner = ReportRunner(verbosity=options["verbosity"])
        failures = runner.run_tests(["accounts.tests"])
        result = runner.result
        counts = Counter(row[2] for row in result.records)
        write_docx(options["output"], result.testsRun, counts, result.records, options["screenshots"])
        self.stdout.write(runner.log_stream.getvalue())
        self.stdout.write(f"Word: {options['output']}")
        if failures or not result.testsRun:
            raise CommandError("Отчёт сохранён. Проверьте результаты тестов.")
