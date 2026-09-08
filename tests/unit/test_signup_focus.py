from django.test import SimpleTestCase

from accounts.forms import CustomSignUpForm


class SignupFocusTests(SimpleTestCase):
    def test_signup_does_not_schedule_autofocus_over_user_input(self):
        form = CustomSignUpForm()
        for name, field in form.fields.items():
            with self.subTest(field=name):
                self.assertNotIn("autofocus", field.widget.attrs)
