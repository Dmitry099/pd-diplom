from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from orders.models import (ConfirmEmailKey, OrderItem, STATE_CHOICES)

from netology_pd.celery import app


@app.task()
def send_auth_key_task(instance_id):
   """
   при создании пользователя отправляем письмо с подтверждением регистрации
   и присваиваем токен
   """
   key, _ = ConfirmEmailKey.objects.get_or_create(user_id=instance_id)

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


@app.task()
def send_email_task(instance_state, instance_id, instance_e_mail):
    """
    при создании заказа отправляем письмо с подтверждением покупателю
    и письмо администратору магазина о размещении заказа
    """

    if instance_state == STATE_CHOICES[1][0]:

        msg = EmailMultiAlternatives(
            # title:
            f"Размещение заказа №{instance_id}",
            # message:
            f"Номер вашего заказа: {instance_id}\n"
            f"Наш оператор свяжется с вами в "
            f"ближайшее время для уточнения делатей заказа\n"
            f"Статуc заказов вы можете посмотреть в разделе 'Заказы'",
            # from:
            settings.EMAIL_HOST_USER,
            # to:
            [instance_e_mail]
        )
        msg.send()

        shop_users = OrderItem.objects.select_related(
            'product_info__shop'
        ).filter(order__id=instance_id).values_list(
            'product_info__shop__user',
            'product_info__shop__user__email'
        )
        for shop_user in shop_users:
            order_items = list(OrderItem.objects.select_related(
                'product_info__shop'
            ).filter(
                order__id=instance_id,
                product_info__shop__user=shop_user[0]
            ).values_list('id', flat=True))
            if len(order_items) > 1:
                order_items = ', '.join(str(x) for x in order_items)
            else:
                order_items = order_items[0]
            msg = EmailMultiAlternatives(
                # title:
                f"Новый заказ №{instance_id}",
                # message:
                f"По новому заказу №{instance_id} заказанны "
                f"позиции с id {order_items}",
                # from:
                settings.EMAIL_HOST_USER,
                # to:
                [shop_user[1]]
            )
            msg.send()