from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_address_order_pointledger'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='points_balance',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
