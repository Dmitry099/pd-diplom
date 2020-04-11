from distutils.util import strtobool

from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
# from ujson import loads as load_json
from yaml import load as load_yaml, Loader

from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.db.models import Q, Sum, F
from django.http import JsonResponse
from requests import get

from .models import Shop, Category, Product, ProductInfo, Parameter, \
    ProductParameter, ConfirmEmailKey
from .serializers import UserSerializer, ProductSerializer, ShopSerializer


# CategorySerializer, \
#     ShopSerializer, ProductInfoSerializer, \
#     OrderItemSerializer, OrderSerializer, ContactSerializer
# from .signals import new_user_registered, new_order


class RegisterView(APIView):
    """
    Регистрация аккаунта
    """

    @staticmethod
    def post(request, *args, **kwargs):
        email = request.data.get('email')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        password = request.data.get('password')
        password_2 = request.data.get('password_2')

        required_fields = [
            email, first_name, last_name, password, password_2
        ]
        if not all(required_fields):
            return JsonResponse(
                {'Status': False,
                 'Errors': 'Не указаны все необходимые аргументы'}
            )
        elif password != password_2:
            return JsonResponse({'Status': False,
                                 'Errors': 'Переданные пароли не совпадают'})
        else:
            try:
                validate_password(password)
            except ValidationError as exp:
                error_list = []
                for error in exp:
                    error_list.append(error)
                return JsonResponse({'Status': False,
                                     'Errors': {'Password_errors': error_list}})
            else:
                user_serializer = UserSerializer(data=request.data)
                try:
                    user_serializer.is_valid(raise_exception=True)
                    user = user_serializer.save()
                    user.set_password(password)
                    user.save()
                    return JsonResponse({'Status': True})
                except ValidationError:
                    return JsonResponse({'Status': False,
                                         'Errors': user_serializer.errors})


class ConfirmAccountView(APIView):
    """
    Подтверждение почтового адреса
    """

    @staticmethod
    def post(request, *args, **kwargs):
        confirmation_key = request.data.get('confirmation_key')
        email = request.data.get('email')
        try:
            key = ConfirmEmailKey.objects.select_related('user').get(
                user__email=email, key=confirmation_key)
        except ConfirmEmailKey.DoesNotExist:
            return JsonResponse({'Status': False,
                                 'Errors': 'Неправильно указан ключ или email'})
        key.user.is_active = True
        key.user.save()
        key.delete()
        return JsonResponse({'Status': True})


class LoginView(APIView):
    """
    Авторизация аккаунта
    """

    @staticmethod
    def post(request, *args, **kwargs):

        username = request.data.get('email')
        password = request.data.get('password')

        required_fields = [
            username, password
        ]
        if not all(required_fields):
            return JsonResponse(
                {'Status': False,
                 'Errors': 'Не указаны все необходимые аргументы'}
            )
        else:
            user = authenticate(request, username=username, password=password)
            if user is not None and user.is_active:
                token, _ = Token.objects.get_or_create(user=user)
                return JsonResponse({'Status': True, 'Token': token.key})
            else:
                return JsonResponse(
                    {'Status': False,
                     'Errors': 'Указанного пользователя не существует '
                               'или аккаунт заблокирован'}
                )


class ProductsView(APIView):
    """
    Список всех товаров c описанием
    """

    @staticmethod
    def get(request, *args, **kwargs):

        products = Product.objects.prefetch_related('product_infos').all()

        products_serializer = ProductSerializer(products, many=True)

        return Response(products_serializer.data)


class ShopsView(APIView):
    """
    Список магазинов
    """

    @staticmethod
    def get(request, *args, **kwargs):

        shops = Shop.objects.all()

        shops_serializer = ShopSerializer(shops, many=True)

        return Response(shops_serializer.data)


class ProductInfoView(APIView):
    """
    Карточка товара
    """

    @staticmethod
    def get(request, product_id=False, *args, **kwargs):

        if not product_id:
            return JsonResponse(
                {'Status': False,
                 'Errors': 'Необходимо передать id товара в параметрах запроса'}
            )

        product = Product.objects.prefetch_related('product_infos').get(
            id=product_id
        )

        products_serializer = ProductSerializer(product)

        return Response(products_serializer.data)


class LoadInfo(APIView):
    """
    Обновление информации о товарах от поставщика
    """

    @staticmethod
    def post(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False,
                                 'Error': 'Для обновления товаров '
                                          'необходима авторизация'},
                                status=403)
        if request.user.type != 'shop':
            return JsonResponse({
                'Status': False,
                'Error': 'Обновлять информацию о товарах '
                         'возможно только магазинам'
            }, status=403)

        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return JsonResponse({'Status': False, 'Error': str(e)})
            else:
                stream = get(url).content
                data = load_yaml(stream, Loader=Loader)
                shop, _ = Shop.objects.get_or_create(name=data['shop'],
                                                     user_id=request.user.id)
                for category in data['categories']:
                    category_object, _ = Category.objects.get_or_create(
                        id=category['id'], name=category['name']
                    )
                    category_object.shops.add(shop.id)
                    category_object.save()

                for item in data['goods']:
                    product, _ = Product.objects.get_or_create(
                        name=item['name'],
                        category_id=item['category'])

                    product_info, _ = ProductInfo.objects.get_or_create(
                        product_id=product.id,
                        external_id=item['id'],
                        model=item['model'],
                        price=item['price'],
                        price_rrc=item['price_rrc'],
                        quantity=item['quantity'],
                        shop_id=shop.id
                    )
                    for name, value in item['parameters'].items():
                        parameter, _ = Parameter.objects.get_or_create(
                            name=name
                        )
                        ProductParameter.objects.create(
                            product_info_id=product_info.id,
                            parameter_id=parameter.id,
                            value=value
                        )

                return JsonResponse({'Status': True})

        return JsonResponse(
            {'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}
        )
