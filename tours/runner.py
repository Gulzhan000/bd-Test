import json
from pathlib import Path
from unittest import TextTestResult
from django.conf import settings
from django.test.runner import DiscoverRunner


class ReportingResult(TextTestResult):
    records = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({"test": test.id(), "status": "PASS"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append({"test": test.id(), "status": "FAIL"})

    def addError(self, test, err):
        super().addError(test, err)
        self.records.append({"test": test.id(), "status": "ERROR"})


class ReportingRunner(DiscoverRunner):
    def get_resultclass(self):
        return ReportingResult

    def run_tests(self, test_labels, **kwargs):
        ReportingResult.records = []
        failures = super().run_tests(test_labels, **kwargs)
        folder = Path(settings.BASE_DIR) / "reports"
        folder.mkdir(exist_ok=True)
        (folder / "test-results.json").write_text(json.dumps(ReportingResult.records, ensure_ascii=False, indent=2))
        return failures
