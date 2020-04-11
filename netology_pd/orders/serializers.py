from rest_framework import serializers

from orders.models import Shop, Contact, User, Product, ProductInfo


class ProductInfoSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductInfo
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):

    product_infos = ProductInfoSerializer(read_only=True, many=True)

    class Meta:
        model = Product
        fields = ('name', 'category', 'product_infos')


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
