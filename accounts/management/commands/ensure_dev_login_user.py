from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create or update a development login user for local/container environments.'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)
        parser.add_argument('--password', required=True)
        parser.add_argument('--email', default='')
        parser.add_argument('--nickname', default='')
        parser.add_argument('--staff', action='store_true')
        parser.add_argument('--premium', action='store_true')
        parser.add_argument(
            '--allow-non-debug',
            action='store_true',
            help='Allow execution when DEBUG=False. Use only for isolated development stacks.',
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options['allow_non_debug']:
            raise CommandError('ensure_dev_login_user is only available when DEBUG=True')

        username = options['username'].strip()
        password = options['password']
        if not username:
            raise CommandError('--username is required')
        if not password:
            raise CommandError('--password is required')

        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={
                'email': options['email'].strip(),
                'nickname': options['nickname'].strip(),
            },
        )

        changed_fields = []
        for field in ('email', 'nickname'):
            value = options[field].strip()
            if value and getattr(user, field) != value:
                setattr(user, field, value)
                changed_fields.append(field)

        if options['staff'] and not user.is_staff:
            user.is_staff = True
            changed_fields.append('is_staff')

        if options['premium'] and not user.is_premium:
            user.is_premium = True
            changed_fields.append('is_premium')

        user.set_password(password)
        changed_fields.append('password')
        user.save()

        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'{action} development login user: {username}'))
