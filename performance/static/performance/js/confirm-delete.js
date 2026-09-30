/*
 * Confirmación de eliminación con SweetAlert2 (Fase 7, Decisión 26).
 *
 * Marcado que espera (parcial performance/partials/delete_button.html):
 *
 *   <form method="post" action="/.../delete/">
 *     {% csrf_token %}
 *     <button type="button" class="js-confirm-delete"
 *             data-title="..." data-text="...">Eliminar</button>
 *   </form>
 *
 * - El botón es type="button": sin JavaScript no envía nada (falla cerrado; no
 *   se puede eliminar por accidente sin confirmar).
 * - Solo si la persona confirma se envía el formulario, por POST y con el token
 *   CSRF que ya lleva. Esto NO reemplaza los chequeos del servidor: la vista
 *   vuelve a verificar sesión, permiso y Delegación.
 * - Título y texto se pasan con `titleText`/`text` (texto plano), nunca con
 *   `title`/`html`, porque incluyen datos del registro y SweetAlert2 no
 *   sanea el HTML.
 * - Si SweetAlert2 no cargó, se usa window.confirm() en su lugar.
 */
(function () {
  'use strict';

  document.addEventListener('click', function (event) {
    var button = event.target.closest('.js-confirm-delete');
    if (!button) { return; }
    var form = button.closest('form');
    if (!form) { return; }
    event.preventDefault();

    var title = button.dataset.title || '¿Eliminar este registro?';
    var text = button.dataset.text || '';

    function submit() {
      // Evita el doble envío (el segundo daría 404: el registro ya no existe).
      button.disabled = true;
      form.submit();
    }

    if (typeof window.Swal === 'undefined') {
      if (window.confirm(text ? title + '\n\n' + text : title)) { submit(); }
      return;
    }

    window.Swal.fire({
      titleText: title,
      text: text,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#b3261e',
      reverseButtons: true,
      focusCancel: true
    }).then(function (result) {
      if (result.isConfirmed) { submit(); }
    });
  });
})();
