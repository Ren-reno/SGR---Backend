# Cierra la migración de attention iniciada en 0002/0003: ya no hay
# ninguna Activity con attention_new nulo (0003 la pobló para toda fila
# existente), así que es seguro eliminar el CharField viejo, renombrar el
# campo puente a su nombre definitivo y quitarle null=True/blank=True.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('performance', '0003_migrate_attention_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='activity',
            name='attention',
        ),
        migrations.RenameField(
            model_name='activity',
            old_name='attention_new',
            new_name='attention',
        ),
        migrations.AlterField(
            model_name='activity',
            name='attention',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='activities',
                to='performance.catalogitem',
                limit_choices_to={'category': 'attention'},
            ),
        ),
    ]
