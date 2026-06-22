import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Validate local development billing environment settings without printing secrets.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--env-file',
            default=os.environ.get('ENV_FILE', '.env.development'),
            help='Development env file to inspect. Defaults to ENV_FILE or .env.development.',
        )
        parser.add_argument(
            '--require-stripe',
            action='store_true',
            help='Fail when Stripe test keys or test Price IDs are still blank.',
        )

    def handle(self, *args, **options):
        env_path = self._resolve_env_file(options['env_file'])
        values = self._read_env_file(env_path)
        warnings = []
        errors = []

        self._record(
            'development-env-file',
            env_path.exists(),
            f'found {self._display_path(env_path)}',
            f'missing {self._display_path(env_path)}',
            errors,
        )
        if not env_path.exists():
            self._finish(warnings, errors)
            return

        gitignore = Path(settings.BASE_DIR) / '.gitignore'
        ignored = gitignore.exists() and '.env.development' in gitignore.read_text(encoding='utf-8')
        self._record(
            'development-env-gitignore',
            ignored,
            '.env.development is ignored',
            '.env.development is not listed in .gitignore',
            errors,
        )

        self._expect_value(values, 'APP_ENV', 'local', errors)
        self._expect_value(values, 'ENVIRONMENT', 'development', errors)
        self._expect_value(values, 'STRIPE_PREMIUM_EXPECTED_CURRENCY', 'jpy', errors)
        self._expect_value(values, 'STRIPE_PREMIUM_MONTHLY_EXPECTED_UNIT_AMOUNT', '480', errors)
        self._expect_value(values, 'STRIPE_PREMIUM_YEARLY_EXPECTED_UNIT_AMOUNT', '4800', errors)

        checkout_enabled = values.get('STRIPE_CHECKOUT_ENABLED', '')
        if checkout_enabled.lower() in {'true', 'false', '1', '0', 'yes', 'no', 'on', 'off'}:
            self.stdout.write(self.style.SUCCESS('OK STRIPE_CHECKOUT_ENABLED: configured'))
        else:
            self._add_error(errors, 'STRIPE_CHECKOUT_ENABLED must be a boolean value')

        public_url = values.get('PUBLIC_SITE_URL', '')
        if public_url.startswith(('http://127.0.0.1', 'http://localhost')):
            self.stdout.write(self.style.SUCCESS('OK PUBLIC_SITE_URL: local URL'))
        else:
            self._add_warning(warnings, 'PUBLIC_SITE_URL should be a local http://127.0.0.1 or http://localhost URL')

        self._stripe_key_check(values, 'STRIPE_SECRET_KEY', 'sk_test_', 'sk_live_', options['require_stripe'], warnings, errors)
        self._stripe_key_check(values, 'STRIPE_PUBLISHABLE_KEY', 'pk_test_', 'pk_live_', options['require_stripe'], warnings, errors)
        self._stripe_key_check(values, 'STRIPE_WEBHOOK_SECRET', 'whsec_', None, options['require_stripe'], warnings, errors)
        self._stripe_key_check(values, 'STRIPE_PREMIUM_PRICE_ID', 'price_', None, options['require_stripe'], warnings, errors)
        self._stripe_key_check(values, 'STRIPE_PREMIUM_YEARLY_PRICE_ID', 'price_', None, options['require_stripe'], warnings, errors)

        raw_text = env_path.read_text(encoding='utf-8-sig')
        forbidden_fragments = ('sk_live_', 'pk_live_')
        leaked_live_fragments = [fragment for fragment in forbidden_fragments if fragment in raw_text]
        if leaked_live_fragments:
            self._add_error(errors, 'development env file contains live Stripe key prefix')
        else:
            self.stdout.write(self.style.SUCCESS('OK no live Stripe key prefixes in development env file'))

        self._finish(warnings, errors)

    def _resolve_env_file(self, raw_path):
        path = Path(raw_path)
        if not path.is_absolute():
            path = Path(settings.BASE_DIR) / path
        return path

    def _read_env_file(self, env_path):
        if not env_path.exists():
            return {}
        values = {}
        for raw_line in env_path.read_text(encoding='utf-8-sig').splitlines():
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
        return values

    def _display_path(self, path):
        try:
            return str(path.relative_to(settings.BASE_DIR))
        except ValueError:
            return str(path)

    def _record(self, name, ok, ok_message, error_message, errors):
        if ok:
            self.stdout.write(self.style.SUCCESS(f'OK {name}: {ok_message}'))
        else:
            self._add_error(errors, error_message)

    def _expect_value(self, values, name, expected, errors):
        value = values.get(name, '')
        if value == expected:
            self.stdout.write(self.style.SUCCESS(f'OK {name}: {expected}'))
            return
        self._add_error(errors, f'{name} must be {expected}')

    def _stripe_key_check(self, values, name, test_prefix, live_prefix, require_stripe, warnings, errors):
        value = values.get(name, '')
        if not value:
            message = f'{name} is blank'
            if require_stripe:
                self._add_error(errors, message)
            else:
                self._add_warning(warnings, message)
            return
        if live_prefix and value.startswith(live_prefix):
            self._add_error(errors, f'{name} must not use a live Stripe key in development')
            return
        if not value.startswith(test_prefix):
            self._add_error(errors, f'{name} must start with {test_prefix}')
            return
        self.stdout.write(self.style.SUCCESS(f'OK {name}: configured with test/development prefix'))

    def _add_warning(self, warnings, message):
        warnings.append(message)
        self.stdout.write(self.style.WARNING(f'WARN {message}'))

    def _add_error(self, errors, message):
        errors.append(message)
        self.stdout.write(self.style.ERROR(f'ERROR {message}'))

    def _finish(self, warnings, errors):
        if errors:
            raise CommandError('billing_development_check failed: ' + '; '.join(errors))
        if warnings:
            self.stdout.write(self.style.WARNING('billing_development_check=warnings'))
            return
        self.stdout.write(self.style.SUCCESS('billing_development_check=ok'))
