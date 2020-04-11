from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from orders.models import ConfirmEmailKey, User


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
