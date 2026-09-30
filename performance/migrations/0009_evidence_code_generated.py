from django.db import migrations, models

# Decisión 33: `Evidence.code` deja de escribirse a mano. Lo asigna el sistema al
# crear la evidencia (`Evidence.save()`, RF-011) y por eso pasa a `editable=False`.
# Solo cambian atributos que no tocan la base (`editable` y `help_text`): la
# columna sigue siendo la misma clave primaria de texto, así que no hay SQL ni
# datos que migrar. Las filas existentes conservan su código tal cual.


class Migration(migrations.Migration):

    dependencies = [
        ('performance', '0008_evidence_review_status_choices'),
    ]

    operations = [
        migrations.AlterField(
            model_name='evidence',
            name='code',
            field=models.CharField(editable=False, help_text='Lo asigna el sistema al guardar (EVID-0001, EVID-0002...) y no se puede cambiar.', max_length=30, primary_key=True, serialize=False),
        ),
    ]
