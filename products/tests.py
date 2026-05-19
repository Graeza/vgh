from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from .models import Product
from users.models import PointLedger

class ProductDetailViewTests(TestCase):
    def setUp(self):
        self.active_product = Product.objects.create(title='Active Product')
        self.inactive_product = Product.objects.create(title='Inactive Product', is_active=False)

    def test_product_detail_resolves_by_slug(self):
        response = self.client.get(reverse('product', kwargs={'slug': self.active_product.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['product'].id, self.active_product.id)

    def test_product_detail_resolves_by_uuid(self):
        response = self.client.get(reverse('product', kwargs={'slug': self.active_product.id}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['product'].id, self.active_product.id)

    def test_product_detail_ignores_inactive_products(self):
        response = self.client.get(reverse('product', kwargs={'slug': self.inactive_product.id}))

        self.assertEqual(response.status_code, 404)


class CheckoutPointRedemptionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='checkout-user', password='password123')
        self.profile = self.user.profile
        self.profile.points_balance = 100
        self.profile.save(update_fields=['points_balance'])
        self.product = Product.objects.create(title='Checkout Product', price='25.00')

    def test_checkout_creates_negative_redeemed_ledger_entry(self):
        session = self.client.session
        session['age_verified'] = True
        session['cart'] = {str(self.product.id): 2}
        session.save()

        self.client.login(username='checkout-user', password='password123')
        response = self.client.post(reverse('checkout'))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('products-list'))

        ledger_entry = PointLedger.objects.get(user=self.profile, event='redeemed')
        self.assertEqual(ledger_entry.points, -50)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points_balance, 50)
