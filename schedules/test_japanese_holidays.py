from datetime import date
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from .holiday_sync import parse_japanese_holiday_csv, sync_japanese_holidays
from .models import JapaneseHoliday
from .tasks import sync_japanese_holidays as sync_japanese_holidays_task


User = get_user_model()


CSV_TEXT = (
    '国民の祝日・休日月日,国民の祝日・休日名称\r\n'
    '2026/1/1,元日\r\n'
    '2026/1/12,成人の日\r\n'
)


class JapaneseHolidaySyncTestCase(TestCase):
    def test_parse_cabinet_office_csv(self):
        holidays = parse_japanese_holiday_csv(CSV_TEXT.encode('cp932'))

        self.assertEqual(
            holidays,
            [
                (date(2026, 1, 1), '元日'),
                (date(2026, 1, 12), '成人の日'),
            ],
        )

    @patch('schedules.holiday_sync.requests.get')
    def test_sync_japanese_holidays_upserts_records(self, get):
        JapaneseHoliday.objects.create(
            date=date(2026, 1, 2),
            name='古い祝日',
            source='cao_csv',
        )
        JapaneseHoliday.objects.create(
            date=date(2026, 1, 3),
            name='手動補正',
            source='manual',
        )
        response = Mock()
        response.content = CSV_TEXT.encode('cp932')
        response.raise_for_status.return_value = None
        get.return_value = response

        result = sync_japanese_holidays(url='https://example.test/holidays.csv')

        self.assertEqual(result['created'], 2)
        self.assertEqual(result['deleted_stale'], 1)
        self.assertEqual(result['total'], 2)
        self.assertEqual(JapaneseHoliday.objects.count(), 3)
        self.assertEqual(
            JapaneseHoliday.objects.get(date=date(2026, 1, 1)).name,
            '元日',
        )
        self.assertFalse(JapaneseHoliday.objects.filter(date=date(2026, 1, 2)).exists())
        self.assertTrue(JapaneseHoliday.objects.filter(date=date(2026, 1, 3)).exists())

    @patch('schedules.holiday_sync.requests.get')
    def test_management_command_runs_sync(self, get):
        response = Mock()
        response.content = CSV_TEXT.encode('cp932')
        response.raise_for_status.return_value = None
        get.return_value = response

        call_command('sync_japanese_holidays', url='https://example.test/holidays.csv')

        self.assertTrue(JapaneseHoliday.objects.filter(date=date(2026, 1, 12)).exists())

    @patch('schedules.holiday_sync.requests.get')
    def test_celery_task_runs_sync(self, get):
        response = Mock()
        response.content = CSV_TEXT.encode('cp932')
        response.raise_for_status.return_value = None
        get.return_value = response

        result = sync_japanese_holidays_task.run()

        self.assertEqual(result['total'], 2)


class JapaneseHolidayApiTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='holiday-user',
            email='holiday-user@example.com',
            password='testpass123',
        )
        JapaneseHoliday.objects.create(date=date(2026, 1, 1), name='元日')
        JapaneseHoliday.objects.create(date=date(2026, 1, 12), name='成人の日')

    def test_holiday_api_returns_holidays_in_range(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('calendar_holidays'),
            {'start': '2026-01-01', 'end': '2026-01-10'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [{'date': '2026-01-01', 'name': '元日'}])

    def test_holiday_api_requires_authentication(self):
        response = self.client.get(
            reverse('calendar_holidays'),
            {'start': '2026-01-01', 'end': '2026-01-10'},
        )

        self.assertEqual(response.status_code, 401)
