"""Paginación con tamaño elegible (Fase 6, paso 6.5 del plan formativo).

Requisito exacto: "Paginación con Paginator, ofreciendo 5/15/30 registros
por página, tamaño guardado en request.session, servidor normaliza o
rechaza valores fuera de ese conjunto." Se elige NORMALIZAR (caer al
default) en vez de rechazar con error 400: un `?per_page=` fuera de rango
es casi siempre alguien editando la URL a mano, no un ataque, y cortar la
página con un error es peor experiencia que ignorar el valor inválido y
mostrar igual el listado con el tamaño anterior.
"""

DEFAULT_PER_PAGE = 15
ALLOWED_PER_PAGE = (5, 15, 30)
SESSION_KEY = 'performance_per_page'  # una sola preferencia para las 4
# entidades del CRUD -- el requisito habla de UNA elección de tamaño de
# página persistida en sesión, no de una por entidad; si el usuario elige
# 30 en Activity y pasa a Evidence, sigue viendo 30 también ahí.


class SessionPaginationMixin:
    """Mixin para `ListView`. Combina con `DelegationScopedQuerysetMixin`
    en la vista concreta; este mixin no toca el queryset, solo decide
    CUÁNTOS resultados de ese queryset entran en cada página.

    Requiere que la vista concreta declare `ordering` (o que el modelo
    tenga `Meta.ordering`): ninguno de Activity/Evidence/Validation/
    Commitment define `ordering` en su `Meta` todavía, y paginar un
    queryset sin orden es no determinista entre páginas -- Django emite
    `UnorderedObjectListWarning` en ese caso. Se corrige acá, en el
    mixin, documentándolo como requisito de cada vista de 6.1 a 6.4 (no
    tocando los modelos de performance, que son alcance de la Fase 2/3, ya
    integradas), por ejemplo: `ordering = ('-date',)` en
    ActivityListView.
    """

    def get_paginate_by(self, queryset):
        requested = self.request.GET.get('per_page')

        if requested is not None:
            try:
                requested_int = int(requested)
            except ValueError:
                requested_int = None
            if requested_int in ALLOWED_PER_PAGE:
                # Valor válido en la URL: pasa a ser la preferencia guardada
                # (así compartir ?per_page=30 con alguien más, o volver con
                # el botón "atrás" del navegador, deja la sesión coherente
                # con lo que se está viendo en pantalla).
                self.request.session[SESSION_KEY] = requested_int
                return requested_int
            # Valor presente pero inválido (fuera del conjunto, o no
            # numérico): se IGNORA -- no pisa la sesión ni rompe la
            # página, cae al tamaño ya guardado o al default.

        return self.request.session.get(SESSION_KEY, DEFAULT_PER_PAGE)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['allowed_per_page'] = ALLOWED_PER_PAGE
        context['current_per_page'] = self.get_paginate_by(None)

        # `get_elided_page_range()` es un MÉTODO de Paginator, no un
        # atributo -- el lenguaje de templates de Django no permite
        # invocar un método con argumentos (`page_obj.paginator.
        # get_elided_page_range(page_obj.number, ...)` sería un
        # TemplateSyntaxError). Se resuelve acá, en Python, y se pasa la
        # lista ya calculada; el partial solo la recorre.
        page_obj = context.get('page_obj')
        if page_obj is not None:
            context['elided_page_range'] = list(
                page_obj.paginator.get_elided_page_range(
                    page_obj.number, on_each_side=1, on_ends=1,
                )
            )
        return context
