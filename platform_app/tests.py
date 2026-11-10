import json
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from .models import (
    User, PasswordResetCode, Transaction, CopyTrader, CopyTraderPlan,
    CopyTradingSubscription, PlatformSettings,
)

STRONG_PASSWORD = 'Sturdy-Pass-9431'


def make_user(username='alice', email='alice@example.com', **extra):
    return User.objects.create_user(
        username=username, email=email, password=STRONG_PASSWORD,
        legal_first_name='Alice', legal_last_name='Smith', **extra,
    )


@patch('platform_app.views.get_country_from_ip', return_value='Testland')
@patch('platform_app.views.send_admin_new_registration_email')
@patch('platform_app.views.send_deposit_reminder')
@patch('platform_app.views.send_welcome_email')
class RegistrationSecurityTests(TestCase):
    def post_register(self, **overrides):
        data = {
            'username': 'newuser', 'email': 'new@example.com', 'password': STRONG_PASSWORD,
            'legal_first_name': 'New', 'legal_last_name': 'User', 'preferred_currency': 'USD',
        }
        data.update(overrides)
        return self.client.post(reverse('register'), data, REMOTE_ADDR='10.0.0.1')

    def test_valid_registration_succeeds(self, *mocks):
        self.post_register()
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_html_in_username_is_rejected(self, *mocks):
        self.post_register(username='<img src=x onerror=alert(1)>')
        self.assertFalse(User.objects.exclude(username='newuser').exists())

    def test_html_in_name_is_rejected(self, *mocks):
        self.post_register(legal_first_name='<b>x</b>')
        self.assertFalse(User.objects.exists())

    def test_weak_password_is_rejected(self, *mocks):
        self.post_register(password='123')
        self.assertFalse(User.objects.exists())

    def test_mass_registration_is_rate_limited(self, *mocks):
        for i in range(7):
            self.post_register(username=f'bulk{i}', email=f'bulk{i}@example.com')
        self.assertEqual(User.objects.count(), 5)


class LoginSecurityTests(TestCase):
    def setUp(self):
        make_user()

    def test_unknown_email_and_wrong_password_look_the_same(self):
        r1 = self.client.post(reverse('login'), {'email': 'nobody@example.com', 'password': 'x'}, follow=True)
        r2 = self.client.post(reverse('login'), {'email': 'alice@example.com', 'password': 'x'}, follow=True)
        self.assertContains(r1, 'Invalid email or password')
        self.assertContains(r2, 'Invalid email or password')
        self.assertNotContains(r1, 'User not found')

    def test_brute_force_locks_out_even_correct_password(self):
        for _ in range(8):
            self.client.post(reverse('login'), {'email': 'alice@example.com', 'password': 'wrong'})
        self.client.post(reverse('login'), {'email': 'alice@example.com', 'password': STRONG_PASSWORD})
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_correct_password_logs_in(self):
        self.client.post(reverse('login'), {'email': 'alice@example.com', 'password': STRONG_PASSWORD})
        self.assertIn('_auth_user_id', self.client.session)


@patch('platform_app.views.send_password_reset_code', return_value={'success': True})
class PasswordResetSecurityTests(TestCase):
    def test_code_guessing_is_capped(self, _send):
        user = make_user()
        self.client.post(reverse('forgot_password'), {'email': user.email})
        real_code = PasswordResetCode.objects.get(user=user, is_used=False).code
        wrong = '000000' if real_code != '000000' else '111111'
        for _ in range(6):
            self.client.post(reverse('verify_reset_code'), {'code': wrong})
        # The real code is burned once guessing is cut off
        self.assertFalse(PasswordResetCode.objects.filter(user=user, is_used=False).exists())
        self.client.post(reverse('verify_reset_code'), {'code': real_code})
        self.assertNotIn('reset_code_id', self.client.session)


@patch('platform_app.views.send_admin_support_message_email')
class SupportChatSecurityTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user())

    def send(self, text):
        return self.client.post(reverse('send_support_message'), json.dumps({'message': text}),
                                content_type='application/json')

    def test_overlong_message_rejected(self, _email):
        self.assertEqual(self.send('a' * 2001).status_code, 400)

    def test_message_flood_is_rate_limited(self, _email):
        codes = [self.send(f'msg {i}').status_code for i in range(16)]
        self.assertEqual(codes[:15], [200] * 15)
        self.assertEqual(codes[15], 429)

    def test_admin_email_is_throttled_per_chat(self, email):
        for i in range(5):
            self.send(f'msg {i}')
        self.assertEqual(email.call_count, 1)


class MoneySafetyTests(TestCase):
    def setUp(self):
        self.user = make_user(account_balance=Decimal('19.91'), total_deposit=Decimal('19.91'))
        self.client.force_login(self.user)
        PlatformSettings.objects.create(copy_trade_auto_invest=True)
        self.trader = CopyTrader.objects.create(
            name='Trader', country='X', country_flag='x', rating=Decimal('4.5'),
            profit_percentage_per_day=Decimal('1'), roi=Decimal('10'), commission_percentage=Decimal('10'),
        )
        CopyTraderPlan.objects.create(trader=self.trader, tier='SILVER', price=Decimal('50'),
                                      commission_percentage=Decimal('10'))

    def test_copy_trade_below_minimum_rejected(self):
        r = self.client.post(reverse('copy_trader_detail', args=[self.trader.id]))
        self.assertFalse(r.json()['success'])
        self.assertFalse(CopyTradingSubscription.objects.exists())
        self.user.refresh_from_db()
        self.assertEqual(self.user.account_balance, Decimal('19.91'))

    @patch('platform_app.views.get_crypto_price', return_value=Decimal('75000'))
    def test_negative_trade_cannot_mint_balance(self, _price):
        # The exact exploit used in production: "buy" BTC with -$1,000,000
        for bad in ('-1000000', '-1', '0', 'NaN'):
            self.client.post(reverse('trading'), {
                'trade_type': 'BUY', 'from_currency': 'USD', 'to_currency': 'BTC', 'from_amount': bad,
            })
        self.user.refresh_from_db()
        self.assertEqual(self.user.account_balance, Decimal('19.91'))

    @patch('platform_app.views.get_crypto_price', return_value=Decimal('75000'))
    def test_normal_trade_still_works(self, _price):
        self.client.post(reverse('trading'), {
            'trade_type': 'BUY', 'from_currency': 'USD', 'to_currency': 'BTC', 'from_amount': '10',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.account_balance, Decimal('9.91'))

    def test_garbage_deposit_amount_does_not_crash(self):
        for bad in ('NaN', 'Infinity', 'abc', '-5', ''):
            r = self.client.post(reverse('deposit'), {'amount': bad})
            self.assertEqual(r.status_code, 302, bad)

    def test_withdrawal_approval_blocked_when_balance_too_low(self):
        admin = User.objects.create_user(username='boss', email='boss@example.com',
                                         password=STRONG_PASSWORD, is_staff=True)
        tx = Transaction.objects.create(user=self.user, transaction_type='WITHDRAWAL',
                                        amount=Decimal('100'), status='PENDING')
        self.client.force_login(admin)
        self.client.post(reverse('admin_transaction_action', args=[tx.id]), {'action': 'approve'})
        tx.refresh_from_db()
        self.assertEqual(tx.status, 'PENDING')

    def test_deposit_cannot_be_approved_twice(self):
        admin = User.objects.create_user(username='boss', email='boss@example.com',
                                         password=STRONG_PASSWORD, is_staff=True)
        tx = Transaction.objects.create(user=self.user, transaction_type='DEPOSIT',
                                        amount=Decimal('100'), status='PENDING')
        self.client.force_login(admin)
        url = reverse('admin_transaction_action', args=[tx.id])
        self.client.post(url, {'action': 'approve'})
        self.client.post(url, {'action': 'approve'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.account_balance, Decimal('119.91'))
