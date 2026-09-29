# Migración de datos, no de esquema. Va entre 0002 (crea CatalogItem +
# attention_new nullable) y 0004 (elimina attention viejo, promueve
# attention_new a attention definitivo).
#
# Por qué 3 migraciones y no 1 sola AlterField:
# `makemigrations` por defecto genera un único AlterField que convierte
# `attention` de CharField a ForeignKey directamente. Eso funciona sobre
# una base vacía, pero esta entrega ya tiene un seed cargado (Decisión 4)
# con valores de texto real en `attention` ("Informes Sociales", etc.) --
# convertir esas filas a FK sin saber a qué CatalogItem.id corresponde
# cada texto no es algo que Django pueda inferir solo, y en SQLite un
# ALTER de tipo de columna sobre datos existentes falla o corrompe la
# columna. La migración de datos intermedia es la forma estándar de
# Django de resolver esto sin perder ni corromper lo ya cargado por el
# seed.
#
# Catálogo poblado con los 6 valores completos de "Tipo Atención" que ya
# fija la Decisión 4 (docs/decisiones.md) -- no solo los 2 que usa
# seed_sgr.py actualmente. El catálogo representa el conjunto de valores
# válidos del negocio, no un espejo de lo que hay cargado en un momento
# dado; poblar solo lo usado hoy dejaría el catálogo incompleto para la
# próxima vez que se cargue una Activity con otro valor válido.

from django.db import migrations


ATTENTION_VALUES = [
    "Informes Sociales",
    "Gestión de Subsidios",
    "Derivación",
    "Otras Gestiones Sociales",
    "Entrega Emergencia",
    "Otros",
]


def populate_catalog_and_migrate_data(apps, schema_editor):
    CatalogItem = apps.get_model('performance', 'CatalogItem')
    Activity = apps.get_model('performance', 'Activity')

    items_by_name = {}
    for name in ATTENTION_VALUES:
        item, _ = CatalogItem.objects.get_or_create(
            category='attention', name=name
        )
        items_by_name[name] = item

    # Cualquier Activity con un valor de `attention` que no esté en la
    # lista fija de arriba (dato ya cargado que no calzara con el
    # catálogo, por ejemplo por un seed distinto en otro entorno) también
    # se resuelve: se crea el CatalogItem faltante sobre la marcha, en vez
    # de dejar la fila sin migrar o fallar la migración completa. Así
    # ninguna Activity existente se queda con attention_new nulo por una
    # discrepancia entre el seed real y la lista de la Decisión 4.
    for activity in Activity.objects.exclude(attention__isnull=True).exclude(attention=''):
        item = items_by_name.get(activity.attention)
        if item is None:
            item, _ = CatalogItem.objects.get_or_create(
                category='attention', name=activity.attention
            )
            items_by_name[activity.attention] = item
        activity.attention_new = item
        activity.save(update_fields=['attention_new'])


def reverse_populate(apps, schema_editor):
    # Reversa simétrica: vuelve a dejar el texto en attention_new no se
    # necesita (ese campo se elimina en 0004), y el CatalogItem creado acá
    # no se borra al revertir porque otra migración de datos posterior
    # podría depender de su existencia -- coherente con que el resto del
    # proyecto no hace borrado físico (Fase 3, patrón deleted_at) salvo
    # que el paso lo pida explícitamente.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('performance', '0002_catalogitem_activity_attention_new'),
    ]

    operations = [
        migrations.RunPython(
            populate_catalog_and_migrate_data, reverse_populate
        ),
    ]
