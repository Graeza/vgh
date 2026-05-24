from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import PointLedger


class AccountPointBalanceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='point-user', password='password123')
        self.profile = self.user.profile

    def test_account_uses_profile_points_balance(self):
        self.profile.points_balance = 250
        self.profile.save(update_fields=['points_balance'])

        PointLedger.objects.create(user=self.profile, event='earned', points=100)

        self.client.login(username='point-user', password='password123')
        response = self.client.get(reverse('account'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['point_balance'], 250)
