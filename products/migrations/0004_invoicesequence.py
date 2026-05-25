from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_product_category_product_cbd_max_product_cbd_min_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='InvoiceSequence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('next_number', models.PositiveIntegerField(default=1)),
            ],
        ),
    ]