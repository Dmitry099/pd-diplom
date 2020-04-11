from rest_framework import serializers

from orders.models import (Category, Contact, OrderItem, Order, Parameter,
                           Product, ProductInfo, ProductParameter, Shop, User)


class ParameterSerializer(serializers.ModelSerializer):

    class Meta:
        model = Parameter
        fields = ('name', )


class ProductParameterSerializer(serializers.ModelSerializer):
    parameter = ParameterSerializer()

    class Meta:
        model = ProductParameter
        fields = ('value', 'parameter')


class ProductInfoSerializer(serializers.ModelSerializer):
    product_parameters = ProductParameterSerializer(read_only=True, many=True)

    class Meta:
        model = ProductInfo
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):

    product_infos = ProductInfoSerializer(read_only=True, many=True)

    class Meta:
        model = Product
        fields = ('name', 'category', 'product_infos')


class ProductsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = ('name', 'category')


class CategoriesSerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = '__all__'


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ('id', 'city', 'street', 'house', 'structure', 'building',
                  'apartment', 'user', 'phone')
        read_only_fields = ('id',)
        extra_kwargs = {
            'user': {'write_only': True}
        }


class UserSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(read_only=True, many=True)

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'company',
                  'position', 'contacts', 'patronymic')
        read_only_fields = ('id',)


class ShopSerializer(serializers.ModelSerializer):

    class Meta:
        model = Shop
        fields = ('id', 'name', 'state')


class OrderProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = ('name',)


class OrderInfoSerializer(serializers.ModelSerializer):
    product = OrderProductSerializer()

    class Meta:
        model = ProductInfo
        fields = ('product', 'price', 'shop')


class OrderUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'patronymic', 'email')


class OrderItemSerializer(serializers.ModelSerializer):
    product_info = OrderInfoSerializer()

    class Meta:
        model = OrderItem
        fields = ('product_info', 'quantity')
        read_only_fields = ('id',)


class OrdersSerializer(serializers.ModelSerializer):
    user = OrderUserSerializer()
    contact = ContactSerializer(read_only=True)
    ordered_items = OrderItemSerializer(read_only=True, many=True)
    total_sum = serializers.IntegerField()

    class Meta:
        model = Order
        fields = ('id', 'ordered_items', 'state', 'dt', 'total_sum', 'user',
                  'contact')
        read_only_fields = ('id',)
