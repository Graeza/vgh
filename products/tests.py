from django.test import TestCase
from django.urls import reverse

from .models import Product

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
