from django.conf import settings
from django.test.runner import DiscoverRunner


class ProjectDiscoverRunner(DiscoverRunner):
    """Limit no-label test discovery to project-owned test modules."""

    default_test_labels = (
        'accounts',
        'schedules',
        'scenarios',
        'tests.unit',
    )

    def build_suite(self, test_labels=None, extra_tests=None, **kwargs):
        if not test_labels:
            test_labels = getattr(
                settings,
                'PROJECT_DEFAULT_TEST_LABELS',
                self.default_test_labels,
            )
        if extra_tests is not None:
            kwargs['extra_tests'] = extra_tests
        return super().build_suite(test_labels, **kwargs)
