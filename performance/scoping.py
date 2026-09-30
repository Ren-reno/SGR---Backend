"""Scoping por Delegación para las vistas web del CRUD (Fase 6, paso 6.0 /
Fase 5 del plan formativo).

El scoping por Delegación ya existe y funciona dentro del Admin desde la
Decisión 6 (`performance/admin.py`, `get_queryset()` de cada ModelAdmin).
Esta Fase 5/6 lo EXTIENDE a las vistas web nuevas -- se reutiliza la misma
regla de negocio, no se rediseña: un superuser ve todo; cualquier otro
usuario ve solo los registros de su propia Delegación, encontrada siguiendo
la cadena de FKs hasta `Employee.delegation`.

Por qué un mixin y no repetir el filtro en cada vista: las 4 entidades del
CRUD web (Activity, Evidence, Validation, Commitment) llegan a
`Employee.delegation` por caminos de distinto largo -- Commitment tiene FK
directa a Delegation (Decisión 16); Activity pasa por 1 salto
(`employee__delegation`); Evidence por 2 (`activity__employee__delegation`);
Validation por 3 (`evidence__activity__employee__delegation`). Ese único
dato que cambia por entidad es `delegation_lookup`; toda la lógica de
"quién ve qué" vive acá una sola vez.
"""

from organization.models import Employee


class DelegationScopedQuerysetMixin:
    """Mixin para `ListView`/`UpdateView`/`DeleteView` basadas en clase.

    Uso: la subclase define `model` (como siempre) y `delegation_lookup`,
    la ruta de campos desde `model` hasta `Delegation`, en sintaxis de
    `filter()` de Django, SIN el sufijo `_id` final (el mixin se lo agrega).
    Cadena vacía `""` para un modelo con FK directa a Delegation.

        class CommitmentListView(DelegationScopedQuerysetMixin, ListView):
            model = Commitment
            delegation_lookup = ""          # Commitment.delegation

        class ActivityListView(DelegationScopedQuerysetMixin, ListView):
            model = Activity
            delegation_lookup = "employee__"

        class EvidenceListView(DelegationScopedQuerysetMixin, ListView):
            model = Evidence
            delegation_lookup = "activity__employee__"

        class ValidationListView(DelegationScopedQuerysetMixin, ListView):
            model = Validation
            delegation_lookup = "evidence__activity__employee__"

    Reglas, en el orden en que se aplican:
    1. Superuser: sin filtrar -- ve todas las Delegaciones (igual que
       `_unrestricted()` en admin.py; ver Decisión 6).
    2. Usuario autenticado SIN `Employee` asociado (p. ej. una cuenta de
       staff creada a mano, sin pasar por el seed): `.none()`, nunca la
       tabla completa. Sin este caso, un `OneToOneField` inexistente
       (`user.employee`) lanzaría `Employee.DoesNotExist` y tumbaría la
       vista con un 500 en vez de mostrar "sin resultados".
    3. Cualquier otro caso: filtrado por la Delegación de su Employee.

    Este mixin SOLO acota el queryset por Delegación -- no reemplaza los
    chequeos de autenticación (`LoginRequiredMixin`, aparte) ni los de
    permiso por acción (que van en cada vista concreta de creación/edición/
    eliminación, no acá: qué puede *ver* alguien de su Delegación es una
    pregunta distinta de qué puede *hacer* con eso).
    """

    delegation_lookup = None  # cada subclase concreta lo define

    def get_delegation_field(self):
        """`"employee__delegation_id"`, `"activity__employee__delegation_id"`,
        etc., a partir de `delegation_lookup`. Falla explícito si una
        subclase se olvidó de definirlo -- mejor un AttributeError claro en
        desarrollo que un filtro silenciosamente vacío en producción."""
        if self.delegation_lookup is None:
            raise NotImplementedError(
                f'{self.__class__.__name__} debe definir '
                f'"delegation_lookup" (ver docstring de '
                f'DelegationScopedQuerysetMixin).'
            )
        return f'{self.delegation_lookup}delegation_id'

    def get_scoped_queryset(self):
        """Queryset base ya acotado por Delegación. Las subclases llaman a
        este método (no a `Model.objects.all()`) desde `get_queryset()`,
        para heredar filtros de estado (p. ej. excluir soft-deleted, cuando
        la Fase 3 lo agregue) sin que el scoping los pise ni viceversa."""
        qs = self.model._default_manager.all()
        user = self.request.user

        # Sin `LoginRequiredMixin` (o si alguna vista lo omitiera), un
        # visitante anónimo llega hasta acá como `AnonymousUser`, que ni
        # siquiera tiene el descriptor de `Employee` -- acceder a
        # `.employee` lanza AttributeError, no Employee.DoesNotExist. Se
        # corta ANTES para no confiar en que la vista puso el mixin de
        # login correctamente: el scoping es robusto por sí mismo.
        if not user.is_authenticated:
            return qs.none()

        if user.is_superuser:
            return qs

        try:
            employee = user.employee
        except Employee.DoesNotExist:
            return qs.none()

        return qs.filter(**{self.get_delegation_field(): employee.delegation_id})

    def get_queryset(self):
        qs = self.get_scoped_queryset()
        # `get_queryset()` reemplaza por completo al de Django (no llama a
        # `super().get_queryset()`), así que el `ordering` de la vista NO
        # se aplicaría solo por declararlo -- `ListView.get_queryset()`
        # original es quien normalmente lee `self.ordering` vía
        # `get_ordering()`; acá se reproduce ese mismo paso explícitamente
        # para no perderlo. Sin esto, paginar sin orden explícito dispara
        # `UnorderedObjectListWarning` y el orden entre páginas queda
        # indeterminado.
        ordering = getattr(self, 'get_ordering', lambda: None)()
        if ordering:
            if isinstance(ordering, str):
                ordering = (ordering,)
            qs = qs.order_by(*ordering)
        return qs
