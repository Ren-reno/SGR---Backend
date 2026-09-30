"""Portada del sitio web (Fase 6, patch 13, Decisión 27).

Un único destino para todos los roles: es a donde lleva el login
(`LOGIN_REDIRECT_URL = 'performance:home'`) y lo que abre el logo del
encabezado. No hay redirects por grupo: la propia plantilla muestra un enlace
por listado, solo si la persona tiene el permiso `view_*` de esa entidad.

Capas de control, del lado del servidor:
- Sesión (`LoginRequiredMixin`): un anónimo que entra a `/` va al login con
  `?next=/`.
- Los enlaces son solo una comodidad: cada listado vuelve a exigir su propio
  permiso y su scoping por Delegación, así que quitar un enlace de la
  plantilla nunca abre ni cierra un acceso por sí solo.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'performance/home.html'
