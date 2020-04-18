import ast
from distutils.util import strtobool

from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from yaml import load as load_yaml, Loader

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import URLValidator
from django.db import IntegrityError, transaction
from django.db.models import Q, F, Sum, Prefetch
from django.http import JsonResponse
from requests import get

from .models import (Category, ConfirmEmailKey, Contact, Order, OrderItem,
                     Parameter, Product, ProductInfo, ProductParameter,
                     Shop, STATE_CHOICES, User)
from .serializers import (CategoriesSerializer, ContactSerializer,
                          OrderItemSerializer, OrdersSerializer,
                          ProductSerializer, ProductInfoSerializer,
                          ProductsSerializer,
                          ShopSerializer, UserSerializer)


class CartException(Exception):
    """Ошибка добавления товаров в коризну

    Атрибуты:
        product_info -- информация о продукте
        reason -- причина возникновения ошибки
    """

    def __init__(self, product_info, reason):
        self.product_info = product_info
        self.reason = reason


class RegisterView(APIView):
    """
    Регистрация аккаунта
    """

    @staticmethod
    def post(request, *args, **kwargs):

        if not {'email', 'first_name', 'last_name',
                'password', 'password_2'}.issubset(request.data):
            return JsonResponse(
                {'Status': False,
                 'Errors': 'Не указаны все необходимые аргументы'}
            )
        elif request.data['password'] != request.data['password_2']:
            return JsonResponse({'Status': False,
                                 'Errors': 'Переданные пароли не совпадают'})
        else:
            try:
                validate_password(request.data['password'])
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
                    user.set_password(request.data['password'])
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

        if not {'email', 'password'}.issubset(request.data):
            return JsonResponse(
                {'Status': False,
                 'Errors': 'Не указаны все необходимые аргументы'}
            )
        else:
            user = authenticate(request, username=request.data['email'],
                                password=request.data['password'])
            if user is not None and user.is_active:
                token, _ = Token.objects.get_or_create(user=user)
                return JsonResponse({'Status': True, 'Token': token.key})
            else:
                return JsonResponse(
                    {'Status': False,
                     'Errors': 'Указанного пользователя не существует '
                               'или аккаунт заблокирован'}
                )


class UserView(APIView):
    """
    Аккаунт пользователя
    """

    @staticmethod
    def get(request, *args, **kwargs):
        """
        Получение данных о пользователе
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False,
                                 'Error': 'Для получения данных пользователя '
                                          'необходима авторизация'},
                                status=403)

        user_serializer = UserSerializer(request.user)

        return Response(user_serializer.data)

    @staticmethod
    def put(request, *args, **kwargs):
        """
        Исправление данных о пользователе
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False,
                                 'Error': 'Для получения данных пользователя '
                                          'необходима авторизация'},
                                status=403)

        if 'password' in request.data:
            try:
                validate_password(request.data['password'])
            except ValidationError as exp:
                error_list = []
                for error in exp:
                    error_list.append(error)
                return JsonResponse({'Status': False,
                                     'Errors': {'Password_errors': error_list}})
            else:
                request.user.set_password(request.data['password'])

        user_serializer = UserSerializer(request.user, data=request.data,
                                         partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False,
                                 'Errors': user_serializer.errors})


class PasswordResetView(APIView):
    """
    Сброс пароля пользователем
    """

    @staticmethod
    def post(request, *args, **kwargs):
        e_mail = request.data.get('email')
        try:
            user = User.objects.get(email=e_mail)
        except User.DoesNotExist:
            return JsonResponse({'Status': False,
                                 'Errors': 'Неправильно указан email'})
        key, _ = ConfirmEmailKey.objects.get_or_create(user=user)
        msg = EmailMultiAlternatives(
            # title:
            f"Confirmation Key for {user.email}",
            # message:
            key.key,
            # from:
            settings.EMAIL_HOST_USER,
            # to:
            [user.email]
        )
        msg.send()
        return JsonResponse({'Status': True})


class PasswordConfirmView(APIView):
    """
    Подтверждение пароля пользователя
    """

    @staticmethod
    def post(request, *args, **kwargs):
        e_mail = request.data.get('email')
        password = request.data.get('password')
        password_2 = request.data.get('password_2')
        confirmation_key = request.data.get('confirmation_key')
        try:
            key = ConfirmEmailKey.objects.select_related('user').get(
                user__email=e_mail, key=confirmation_key)
        except ConfirmEmailKey.DoesNotExist:
            return JsonResponse({'Status': False,
                                 'Errors': 'Неправильно указан ключ или email'})
        if password != password_2:
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
                key.user.set_password(password)
                key.user.save()
                key.delete()
                return JsonResponse({'Status': True})


class ShopsView(APIView):
    """
    Список магазинов
    """

    @staticmethod
    def get(request, *args, **kwargs):
        shops = Shop.objects.all()

        shops_serializer = ShopSerializer(shops, many=True)

        return Response(shops_serializer.data)


class ProductsView(APIView):
    """
    Список всех товаров без описания и привязки к магазину
    """

    @staticmethod
    def get(request, *args, **kwargs):
        shop = request.data.get('shop')
        category = request.data.get('category')

        filter = Q(shop__state=True)

        if shop:
            filter = filter & Q(shop_id=shop)

        if category:
            filter = filter & Q(product__category_id=category)

        products = ProductInfo.objects.filter(
            filter).select_related(
            'shop', 'product__category').prefetch_related(
            'product_parameters__parameter').distinct()

        products_serializer = ProductInfoSerializer(products, many=True)

        return Response(products_serializer.data)


class CategoriesView(APIView):
    """
    Список всех категорий
    """

    @staticmethod
    def get(request, *args, **kwargs):
        categories = Category.objects.all()

        products_serializer = CategoriesSerializer(categories, many=True)

        return Response(products_serializer.data)


class ProductInfoView(APIView):
    """
    Карточка товара с описанием и привязкой к магазинам
    """

    @staticmethod
    def get(request, product_id=False, *args, **kwargs):
        if not product_id:
            return JsonResponse(
                {'Status': False,
                 'Errors': 'Необходимо передать id товара в параметрах запроса'}
            )
        try:
            product = Product.objects.prefetch_related(Prefetch(
                'product_infos',
                queryset=ProductInfo.objects.filter(shop__state=True)
            )).get(id=product_id)
        except Product.DoesNotExist:
            return JsonResponse({
                'Status': False,
                'Error': 'Товара с указанным id не существует'
            })
        products_serializer = ProductSerializer(product)

        return Response(products_serializer.data)


class CartView(APIView):
    """
    Корзина
    """

    @staticmethod
    def get(request, *args, **kwargs):
        """
        Содержимое корзины
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False,
                                 'Error': 'Для получения данных корзины '
                                          'в корзину необходима авторизация'},
                                status=403)

        if request.user.type != 'buyer':
            return JsonResponse({
                'Status': False,
                'Error': 'Корзина доступна только покупателям'
            }, status=403)

        cart, _ = Order.objects.get_or_create(
            user=request.user,
            state=STATE_CHOICES[0][0],
        )
        order_items = OrderItem.objects.filter(order=cart).select_related(
            'product_info__product', 'product_info__shop').annotate(
            total_sum=Sum(
                F('quantity') * F(
                    'product_info__price'
                )
            )
        )
        order_items_serializer = OrderItemSerializer(order_items, many=True)

        return Response(order_items_serializer.data)

    @staticmethod
    def delete(request, *args, **kwargs):
        """
        Удаление товаров из корзины
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False,
                                 'Error': 'Для удаления товаров '
                                          'из корзины необходима авторизация'},
                                status=403)

        if request.user.type != 'buyer':
            return JsonResponse({
                'Status': False,
                'Error': 'Удалять товары из коризны'
                         ' возможно только покупателям'
            }, status=403)

        order_items = request.data.get('order_items')
        if not order_items:
            return JsonResponse(
                {'Status': False,
                 'Errors': 'Не передан параметр с инофрмацией о товарах'
                           'в теле запроса'}
            )

        order_items = order_items.split(',')
        try:
            with transaction.atomic():
                for item in order_items:
                    order_item = OrderItem.objects.get(id=item.strip())
                    if order_item.order.user != request.user:
                        return JsonResponse({
                            'Status': False,
                            'Error': 'Нельзя вносить изменения '
                                     'не в свою корзину'
                        })
                    else:
                        order_item.delete()
        except OrderItem.DoesNotExist:
            return JsonResponse({
                'Status': False,
                'Error': 'Информация о товаре отсутствует'
            })
        else:
            return JsonResponse({'Status': True})

    @staticmethod
    def put(request, *args, **kwargs):
        """
        Изменение количества товаров в корзине
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False,
                                 'Error': 'Для изменения товаров '
                                          'в корзине необходима авторизация'},
                                status=403)

        if request.user.type != 'buyer':
            return JsonResponse({
                'Status': False,
                'Error': 'Изменять товары в коризне'
                         ' возможно только покупателям'
            }, status=403)

        data = request.data.get('items')
        if not data:
            return JsonResponse(
                {'Status': False,
                 'Errors': 'Не передан параметр с информацией о товарах'
                           'в теле запроса'}
            )
        try:
            data = ast.literal_eval(data)
        except SyntaxError:
            JsonResponse({'Status': False, 'Errors': 'Неверный формат запроса'})

        try:
            with transaction.atomic():
                for item in data:
                    order_item = OrderItem.objects.get(id=item['id'])
                    if order_item.product_info.quantity < item['quantity']:
                        raise CartException(
                            product_info=order_item.product_info,
                            reason='quantity')
                    elif order_item.order.user != request.user:
                        return JsonResponse({
                            'Status': False,
                            'Error': 'Нельзя вносить изменения не в свою корзину'
                        })
                    else:
                        order_item.quantity = item['quantity']
                        order_item.save()
        except CartException as exc:
            if exc.reason == 'quantity':
                return JsonResponse({
                    'Status': False,
                    'Error': 'У магазина {} недостаточное количество товара {}'
                             ' для добавления в корзину.Всего в магазине {} '
                             'штук, доступных для добавления '
                             'в корзину'.format(exc.product_info.shop.name,
                                                exc.product_info.product.name,
                                                exc.product_info.quantity)
                })
        except OrderItem.DoesNotExist:
            return JsonResponse({
                'Status': False,
                'Error': 'Информация о товаре отсутствует'
            })

        return JsonResponse({'Status': True})

    @staticmethod
    def post(request, *args, **kwargs):
        """
        Добавление товаров в коризну
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False,
                                 'Error': 'Для добавления товаров '
                                          'в корзину необходима авторизация'},
                                status=403)

        if request.user.type != 'buyer':
            return JsonResponse({
                'Status': False,
                'Error': 'Добавлять товары в коризну'
                         ' возможно только покупателям'
            }, status=403)

        data = request.data.get('items')
        if not data:
            return JsonResponse(
                {'Status': False,
                 'Errors': 'Не передан параметр с инофрмацией о товарах'
                           'в теле запроса'}
            )
        cart, _ = Order.objects.get_or_create(
            user=request.user,
            state=STATE_CHOICES[0][0],
        )
        try:
            data = ast.literal_eval(data)
        except SyntaxError:
            JsonResponse({'Status': False, 'Errors': 'Неверный формат запроса'})

        try:
            with transaction.atomic():
                for item in data:
                    product_info = ProductInfo.objects.get(
                        id=item['product_info'])
                    if product_info.quantity < item['quantity']:
                        raise CartException(product_info=product_info,
                                            reason='quantity')
                    elif not product_info.shop.state:
                        raise CartException(product_info=product_info,
                                            reason='state')
                    try:
                        OrderItem.objects.create(
                            order=cart,
                            product_info=product_info,
                            quantity=item['quantity']
                        )
                    except IntegrityError:
                        return JsonResponse({
                            'Status': False,
                            'Error': 'В корзину уже добавлен товар с '
                                     'информацией по id {}. Если хотите '
                                     'изменить информацию по данному id '
                                     'используйте метод PUT'.format(
                                        product_info.id
                                     )
                        })
        except CartException as exc:
            if exc.reason == 'quantity':
                return JsonResponse({
                    'Status': False,
                    'Error': 'У магазина {} недостаточное количество товара {}'
                             ' для добавления в корзину.Всего в магазине {} '
                             'штук, доступных для добавления '
                             'в корзину'.format(exc.product_info.shop.name,
                                                exc.product_info.product.name,
                                                exc.product_info.quantity)
                })
            elif exc.reason == 'state':
                return JsonResponse({
                    'Status': False,
                    'Error': 'Магазин {} не принимает заказы '
                             'в данный момент '.format(
                                exc.product_info.shop.name
                             )
                })
        return JsonResponse({'Status': True})


class OrdersView(APIView):
    """
    Заказы
    """

    @staticmethod
    def get(request, *args, **kwargs):
        """
        Получить все имеющиеся заказы
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False,
                                 'Error': 'Для получения информации о заказах '
                                          'необходима авторизация'},
                                status=403)

        if request.user.type != 'buyer':
            return JsonResponse({
                'Status': False,
                'Error': 'Заказы доступны только покупателям'
            }, status=403)
        orders = Order.objects.select_related('contact').prefetch_related(
            'ordered_items'
        ).filter(user=request.user).exclude(state=STATE_CHOICES[0][0]).annotate(
            total_sum=Sum(
                F('ordered_items__quantity') * F(
                    'ordered_items__product_info__price'
                )
            )
        ).distinct()
        orders_serializer = OrdersSerializer(orders, many=True)

        return Response(orders_serializer.data)


class OrderView(APIView):
    """
    Заказ
    """

    @staticmethod
    def get(request, *args, **kwargs):
        """
        Получить расифровку по заказу
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False,
                                 'Error': 'Для получения информации о заказах '
                                          'необходима авторизация'},
                                status=403)

        if request.user.type != 'buyer':
            return JsonResponse({
                'Status': False,
                'Error': 'Заказы доступны только покупателям'
            }, status=403)
        try:
            orders = Order.objects.select_related('contact').prefetch_related(
                'ordered_items').annotate(
                total_sum=Sum(
                    F('ordered_items__quantity') * F(
                        'ordered_items__product_info__price'
                    )
                )
            ).get(
                id=request.data.get('id')
            )
        except Order.DoesNotExist:
            return JsonResponse({
                'Status': False,
                'Error': 'Указанный id заказа не существует'
            })
        orders_serializer = OrdersSerializer(orders)

        return Response(orders_serializer.data)

    @staticmethod
    def post(request, *args, **kwargs):
        """
        Создать заказ
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False,
                                 'Error': 'Для создания заказа '
                                          'необходима авторизация'},
                                status=403)

        if request.user.type != 'buyer':
            return JsonResponse({
                'Status': False,
                'Error': 'Создать заказ доступно только покупателям'
            }, status=403)

        if not {'id', 'contact_id'}.issubset(request.data):
            return JsonResponse(
                {'Status': False,
                 'Errors': 'Не указаны все необходимые аргументы'}
            )

        try:
            order = Order.objects.get(
                id=request.data.get('id'),
                state=STATE_CHOICES[0][0],
            )
            contact = Contact.objects.get(id=request.data.get('contact_id'))

        except Contact.DoesNotExist:
            return JsonResponse({
                'Status': False,
                'Error': 'Указанного id контакта не существует'
            })
        except Order.DoesNotExist:
            return JsonResponse({
                'Status': False,
                'Error': 'Указанный id корзины не существует'
            })
        else:
            order.contact = contact
            order.state = ''.join(STATE_CHOICES[1][0])
            order.save()
            return JsonResponse({'Status': True})


class ContactView(APIView):
    """
    Контакты пользователя
    """

    @staticmethod
    def get(request, *args, **kwargs):
        """
        Получить имеющиеся контакты
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False,
                                 'Error': 'Для получения контактов '
                                          'необходима авторизация'},
                                status=403)

        contact = Contact.objects.filter(user=request.user)
        contact_serializer = ContactSerializer(contact, many=True)

        return Response(contact_serializer.data)

    @staticmethod
    def delete(request, *args, **kwargs):
        """
        Удалить контакты
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False,
                                 'Error': 'Для удаления контактов '
                                          'необходима авторизация'},
                                status=403)

        contacts_id = request.data.get('contacts_id')
        if not contacts_id:
            return JsonResponse(
                {'Status': False,
                 'Errors': 'Не передан параметр с информацией о контактах'
                           'в теле запроса'}
            )

        contacts_id = contacts_id.split(',')
        try:
            with transaction.atomic():
                for item in contacts_id:
                    contact = Contact.objects.get(id=item.strip())
                    if contact.user != request.user:
                        return JsonResponse({
                            'Status': False,
                            'Error': 'Нельзя удалять чужие контакты '
                        })
                    else:
                        contact.delete()
        except OrderItem.DoesNotExist:
            return JsonResponse({
                'Status': False,
                'Error': 'id контакта не существует'
            })
        else:
            return JsonResponse({'Status': True})

    @staticmethod
    def post(request, *args, **kwargs):
        """
        Создать контакт
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False,
                                 'Error': 'Для создания контакта '
                                          'необходима авторизация'},
                                status=403)

        if not {'city', 'street', 'phone'}.issubset(request.data):
            return JsonResponse(
                {'Status': False,
                 'Errors': 'Не указаны все необходимые аргументы'}
            )

        request.data._mutable = True
        request.data.update({'user': request.user.id})
        serializer = ContactSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': serializer.errors})

    @staticmethod
    def put(request, *args, **kwargs):
        """
        Изменить контакт
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False,
                                 'Error': 'Для изменения контакта '
                                          'необходима авторизация'},
                                status=403)

        if not {'city', 'street', 'phone', 'id'}.issubset(request.data):
            return JsonResponse(
                {'Status': False,
                 'Errors': 'Не указаны все необходимые аргументы'}
            )
        try:
            contact = Contact.objects.get(id=request.data.get('id'))
        except Contact.DoesNotExist:
            return JsonResponse({
                'Status': False,
                'Error': 'Указанный id контакта не существует'
            })
        else:
            if contact.user != request.user:
                return JsonResponse({
                    'Status': False,
                    'Error': 'Нельзя вносить изменения '
                             'не в свои контакты'
                })
            serializer = ContactSerializer(contact, data=request.data,
                                           partial=True)
            if serializer.is_valid():
                serializer.save()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False,
                                     'Errors': serializer.errors})


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


class StateChange(APIView):
    """
    Статус получения заказов магазина
    """

    @staticmethod
    def get(request, *args, **kwargs):
        """
        Получить статус заказов магазина
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False,
                                 'Error': 'Для получения статуса '
                                          'необходима авторизация'},
                                status=403)
        if request.user.type != 'shop':
            return JsonResponse({
                'Status': False,
                'Error': 'Получать инфомрацию о статусе '
                         'возможно только магазинам'
            }, status=403)

        shop = Shop.objects.get(user=request.user)

        shops_serializer = ShopSerializer(shop)

        return Response(shops_serializer.data)

    @staticmethod
    def put(request, *args, **kwargs):
        """
        Изменить статус получения заказов магазина
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False,
                                 'Error': 'Для обновления статуса '
                                          'необходима авторизация'},
                                status=403)
        if request.user.type != 'shop':
            return JsonResponse({
                'Status': False,
                'Error': 'Обновлять статус '
                         'возможно только магазинам'
            }, status=403)

        state = request.data.get('state')
        shop = Shop.objects.get(user=request.user)
        if not state:
            return JsonResponse(
                {'Status': False,
                 'Errors': 'Не указаны все необходимые аргументы'}
            )
        try:
            shop.state = strtobool(state)
        except ValueError:
            return JsonResponse(
                {'Status': False,
                 'Errors': 'Переданный параметр статуса некорректен'}
            )
        else:
            shop.save()
            return JsonResponse({'Status': True})


class ShopOrders(APIView):
    """
    Заказы магазина
    """

    @staticmethod
    def get(request, *args, **kwargs):
        """
        Получить заказы магазина
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False,
                                 'Error': 'Для получения статуса '
                                          'необходима авторизация'},
                                status=403)
        if request.user.type != 'shop':
            return JsonResponse({
                'Status': False,
                'Error': 'Получать инфомрацию о статусе '
                         'возможно только магазинам'
            }, status=403)

        orders = Order.objects.select_related('contact').prefetch_related(
            'ordered_items').exclude(
            state=STATE_CHOICES[0][0]
        ).filter(
            ordered_items__product_info__shop__user=request.user
        ).annotate(
            total_sum=Sum(
                F('ordered_items__quantity') * F(
                    'ordered_items__product_info__price'
                )
            )
        ).distinct()
        orders_serializer = OrdersSerializer(orders, many=True)

        return Response(orders_serializer.data)
