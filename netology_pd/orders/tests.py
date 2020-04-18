import json

from django.core.exceptions import ViewDoesNotExist
from django.test import SimpleTestCase, TestCase
from django.urls import get_callable, reverse
from rest_framework.authtoken.models import Token

from orders.models import (Shop, Category, User, Product,
                           ProductInfo, Parameter, ProductParameter)
from orders.views import empty_view


class ViewLoadingTests(SimpleTestCase):
    def test_view_loading(self):
        self.assertEqual(get_callable('orders.views.empty_view'),
                         empty_view)
        self.assertEqual(get_callable(empty_view), empty_view)

    def test_view_does_not_exist(self):
        msg = "View does not exist in module orders.views."
        with self.assertRaisesMessage(ViewDoesNotExist, msg):
            get_callable('orders.views.i_should_not_exist')

    def test_non_string_value(self):
        msg = "'1' is not a callable or a dot-notation path"
        with self.assertRaisesMessage(ViewDoesNotExist, msg):
            get_callable(1)

    def test_string_without_dot(self):
        msg = "Could not import 'test'. The path must be fully qualified."
        with self.assertRaisesMessage(ImportError, msg):
            get_callable('test')

    def test_module_does_not_exist(self):
        with self.assertRaisesMessage(ImportError, "No module named 'foo'"):
            get_callable('foo.bar')

    def test_parent_module_does_not_exist(self):
        msg = 'Parent module orders.foo does not exist.'
        with self.assertRaisesMessage(ViewDoesNotExist, msg):
            get_callable('orders.foo.bar')


class ShopsViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Создать 10 Shops
        number_of_shops = 10
        for shop_num in range(number_of_shops):
            Shop.objects.create(name='Shop %s' % shop_num)

    def test_view_url_exists_at_desired_location(self):
        resp = self.client.get('http://127.0.0.1:8000/api/shops')
        self.assertNotEqual(resp.status_code, 404)

    def test_view_url_accessible_by_name(self):
        resp = self.client.get(reverse('orders:shops'))
        self.assertNotEqual(resp.status_code, 404)

    def test_lists_all_shops(self):
        count = Shop.objects.all().count()
        resp = self.client.get(reverse('orders:shops'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['count'] == count)


class CategoriesViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Создать 5 Categories
        number_of_categories = 5
        for category_num in range(number_of_categories):
            Category.objects.create(name='Category %s' % category_num)

    def test_view_url_exists_at_desired_location(self):
        resp = self.client.get('http://127.0.0.1:8000/api/categories')
        self.assertNotEqual(resp.status_code, 404)

    def test_view_url_accessible_by_name(self):
        resp = self.client.get(reverse('orders:categories'))
        self.assertNotEqual(resp.status_code, 404)

    def test_lists_all_categories(self):
        count = Category.objects.all().count()
        resp = self.client.get(reverse('orders:categories'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['count'] == count)


class CategoriesViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Создать 5 Categories
        number_of_categories = 5
        for category_num in range(number_of_categories):
            Category.objects.create(name='Category %s' % category_num)

    def test_view_url_exists_at_desired_location(self):
        resp = self.client.get('http://127.0.0.1:8000/api/categories')
        self.assertNotEqual(resp.status_code, 404)

    def test_view_url_accessible_by_name(self):
        resp = self.client.get(reverse('orders:categories'))
        self.assertNotEqual(resp.status_code, 404)

    def test_lists_all_categories(self):
        count = Category.objects.all().count()
        resp = self.client.get(reverse('orders:categories'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['count'] == count)


class UserRegisterViewTest(TestCase):

    def test_view_url_exists_at_desired_location(self):
        resp = self.client.get('http://127.0.0.1:8000/api/user/register')
        self.assertNotEqual(resp.status_code, 404)

    def test_view_url_accessible_by_name(self):
        resp = self.client.get(reverse('orders:user-register'))
        self.assertNotEqual(resp.status_code, 404)

    def test_user_register(self):
        email = input('input email')
        first_name = input('input first_name')
        last_name = input('input last_name')
        password = input('input password')
        password_2 = input('input password_2')
        patronymic = input('input patronymic')
        company = input('input company')
        position = input('input position')

        resp = self.client.post(reverse('orders:user-register'), data={
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'password': password,
            'password_2': password_2,
            'patronymic': patronymic,
            'company': company,
            'position': position,

        })
        self.assertEqual(resp.status_code, 200)

        key = input('input key from email')
        resp_2 = self.client.post(reverse('orders:user-register-confirm'),
                                  data={
                                      'email': email,
                                      'key': key,
                                  })
        self.assertEqual(resp_2.status_code, 200)


class LoginViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Создать User
        cls.test_user1 = User.objects.create_user(email='testuser1@mail.ru',
                                                  password=12345,
                                                  first_name='testuser1',
                                                  last_name='testuser1',
                                                  is_active=True)

    def test_view_url_exists_at_desired_location(self):
        resp = self.client.get('http://127.0.0.1:8000/api/user/login')
        self.assertNotEqual(resp.status_code, 404)

    def test_view_url_accessible_by_name(self):
        resp = self.client.get(reverse('orders:user-login'))
        self.assertNotEqual(resp.status_code, 404)

    def test_user_login(self):
        resp = self.client.post(reverse('orders:user-login'), data={
            'email': 'testuser1@mail.ru',
            'password': 12345,
        })
        self.assertEqual(resp.status_code, 200)
        token = Token.objects.get(user=LoginViewTest.test_user1)
        resp_token = json.loads(resp.content)['Token']
        self.assertEqual(resp_token, token.key)


class ProductViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # создать Shops
        cls.shop_1 = Shop.objects.create(name='Shop 1')
        cls.shop_2 = Shop.objects.create(name='Shop2')
        # Создать 2 Categories
        cls.category_1 = Category.objects.create(name='Category 1')
        cls.category_1.shops.add(cls.shop_1)
        cls.category_2 = Category.objects.create(name='Category 1')
        cls.category_2.shops.add(cls.shop_2)
        # Создать 2 Product
        cls.product = Product.objects.create(name='Product 1',
                                             category=cls.category_1)

        cls.product_info = ProductInfo.objects.create(model='New',
                                                      external_id=1111,
                                                      product=cls.product,
                                                      shop=cls.shop_1,
                                                      quantity=1,
                                                      price=100,
                                                      price_rrc=110)
        cls.parameter = Parameter.objects.create(name='First')
        ProductParameter.objects.create(product_info=cls.product_info,
                                        parameter=cls.parameter,
                                        value='Value')
        cls.product_2 = Product.objects.create(name='Product 2',
                                               category=cls.category_2)

        cls.product_info_2 = ProductInfo.objects.create(model='New2',
                                                        external_id=1122,
                                                        product=cls.product_2,
                                                        shop=cls.shop_2,
                                                        quantity=2,
                                                        price=102,
                                                        price_rrc=112)
        ProductParameter.objects.create(product_info=cls.product_info_2,
                                        parameter=cls.parameter,
                                        value='Value')

    def test_view_url_exists_at_desired_location(self):
        resp = self.client.get('http://127.0.0.1:8000/api/products')
        self.assertNotEqual(resp.status_code, 404)

    def test_view_url_accessible_by_name(self):
        resp = self.client.get(reverse('orders:products'))
        self.assertNotEqual(resp.status_code, 404)

    def test_shop_state(self):
        resp = self.client.get(reverse('orders:products'))
        self.assertEqual(resp.status_code, 200)
        resp_json = json.loads(resp.content)
        self.assertEqual(len(resp_json), 2)

