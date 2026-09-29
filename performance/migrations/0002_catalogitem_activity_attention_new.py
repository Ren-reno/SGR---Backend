# Generated manually (no via makemigrations) -- ver comentario en
# 0003_migrate_attention_data.py sobre por qué el cambio de attention se
# divide en 3 migraciones (esquema / datos / esquema) en vez de una sola
# AlterField como generaría `makemigrations` por defecto.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('performance', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CatalogItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('attention', 'Tipo Atención')], max_length=30)),
                ('name', models.CharField(max_length=100)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ('category', 'name'),
            },
        ),
        migrations.AddConstraint(
            model_name='catalogitem',
            constraint=models.UniqueConstraint(fields=('category', 'name'), name='unique_catalog_item_per_category'),
        ),
        # Campo puente temporal: FK nullable en paralelo al CharField
        # `attention` existente. Se puebla en la migración de datos
        # siguiente (0003) y se promueve a `attention` definitivo en
        # 0004, una vez que cada fila ya tiene su CatalogItem asignado.
        migrations.AddField(
            model_name='activity',
            name='attention_new',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='activities_new',
                to='performance.catalogitem',
                limit_choices_to={'category': 'attention'},
            ),
        ),
    ]
