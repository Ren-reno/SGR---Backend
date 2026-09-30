from django.db import migrations, models

# Decisión 30: `Evidence.review_status` pasa de texto libre a un conjunto cerrado
# y se guarda siempre en minúscula. Hasta ahora convivían dos grafías: el default
# del modelo era `pendiente`, el seed guardaba `Pendiente` y la acción masiva del
# Admin guardaba `Aprobada`.
REVIEW_STATUS_VALUES = ('pendiente', 'aprobada', 'rechazada')


def normalize_review_status(apps, schema_editor):
    Evidence = apps.get_model('performance', 'Evidence')
    # `_base_manager` y no `objects`: incluye también las evidencias eliminadas
    # lógicamente (Decisión 26), que si no quedarían con la grafía antigua.
    rows = Evidence._base_manager.all()
    for value in REVIEW_STATUS_VALUES:
        rows.filter(review_status__iexact=value).exclude(
            review_status=value
        ).update(review_status=value)
    # Un valor que no sea una variante de mayúsculas de los tres miembros no se
    # toca: no hay una regla para adivinar a cuál correspondería.


class Migration(migrations.Migration):

    dependencies = [
        ('performance', '0007_soft_delete'),
    ]

    operations = [
        migrations.AlterField(
            model_name='evidence',
            name='review_status',
            field=models.CharField(choices=[('pendiente', 'Pendiente'), ('aprobada', 'Aprobada'), ('rechazada', 'Rechazada')], default='pendiente', max_length=30),
        ),
        # Sin marcha atrás útil: no se puede saber qué grafía tenía cada fila.
        migrations.RunPython(normalize_review_status, migrations.RunPython.noop),
    ]
