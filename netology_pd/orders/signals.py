from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from orders.models import (ConfirmEmailKey, Order, OrderItem,
                           STATE_CHOICES, User)


@receiver(post_save, sender=User)
def send_auth_key(sender, instance=None, created=False, **kwargs):
    """
    при создании пользователя отправляем письмо с подтверждением регистрации
    и присваиваем токен
    """
    if created:
        key, _ = ConfirmEmailKey.objects.get_or_create(user_id=instance.id)

        msg = EmailMultiAlternatives(
            # title:
            f"Confirmation Key for {key.user.email}",
            # message:
            key.key,
            # from:
            settings.EMAIL_HOST_USER,
            # to:
            [key.user.email]
        )
        msg.send()


@receiver(post_save, sender=Order)
def send_email(sender, instance=None, created=False, **kwargs):
    """
    при создании заказа отправляем письмо с подтверждением покупателю
    и письмо администратору магазина о размещении заказа
    """

    if instance.state == STATE_CHOICES[1][0]:

        msg = EmailMultiAlternatives(
            # title:
            f"Размещение заказа №{instance.id}",
            # message:
            f"Номер вашего заказа: {instance.id}\n"
            f"Наш оператор свяжется с вами в "
            f"ближайшее время для уточнения делатей заказа\n"
            f"Статуc заказов вы можете посмотреть в разделе 'Заказы'",
            # from:
            settings.EMAIL_HOST_USER,
            # to:
            [instance.user.email]
        )
        msg.send()

        shop_users = OrderItem.objects.select_related(
            'product_info__shop'
        ).filter(order__id=instance.id).values_list(
            'product_info__shop__user',
            'product_info__shop__user__email'
        )
        for shop_user in shop_users:
            order_items = list(OrderItem.objects.select_related(
                'product_info__shop'
            ).filter(
                order__id=instance.id,
                product_info__shop__user=shop_user[0]
            ).values_list('id', flat=True))
            if len(order_items) > 1:
                order_items = ', '.join(order_items)
            else:
                order_items = order_items[0]
            msg = EmailMultiAlternatives(
                # title:
                f"Новый заказ №{instance.id}",
                # message:
                f"По новому заказу №{instance.id} заказанны "
                f"позиции с id {order_items}",
                # from:
                settings.EMAIL_HOST_USER,
                # to:
                [shop_user[1]]
            )
            msg.send()

