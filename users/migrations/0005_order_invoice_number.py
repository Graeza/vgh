from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_alter_pointledger_event'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='invoice_number',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
    ]
