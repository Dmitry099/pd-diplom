from django.apps import AppConfig


class OrdersConfig(AppConfig):
    name = 'orders'

    def ready(self):
        """
        импортируем сигналы
        """
        import orders.signals