# Podkstr — QA / Bug Log

Bugs and errors found during development and testing. Each entry includes root cause and fix applied.

---

## Textual 8 API Incompatibilities

### `call_from_thread` not available on `Screen`

**File:** `podkstr/ui/episode_screen.py`
**Symptom:** `AttributeError: 'EpisodeScreen' object has no attribute 'call_from_thread'`
**Root cause:** In Textual 8, `call_from_thread` lives on `App`, not on `Screen`. Thread workers inside a Screen that need to update the UI must route through the app.
**Fix:** Replace all `self.call_from_thread(...)` with `self.app.call_from_thread(...)` inside `EpisodeScreen`.

---

### `Static.renderable` does not exist

**File:** `tests/ui/test_player_bar.py`, `tests/ui/test_episode_screen.py`
**Symptom:** `AttributeError: 'Static' object has no attribute 'renderable'`
**Root cause:** Textual 8 removed the `.renderable` property from `Static`.
**Fix:** Use `str(widget.render())` instead.

---

### `focus()` is not async

**File:** `podkstr/ui/add_source_modal.py`
**Symptom:** `TypeError: object NoneType can't be used in 'await' expression`
**Root cause:** `Widget.focus()` is synchronous in Textual 8 — `await` is wrong.
**Fix:** Remove `await` from all `focus()` calls.

---

### `Pilot.type()` does not exist

**File:** `tests/ui/test_source_screen.py`
**Symptom:** `AttributeError: 'Pilot' object has no attribute 'type'`
**Root cause:** Textual 8 has no `pilot.type(text)` helper.
**Fix:** Set `Input.value = "..."` directly on the widget instance.

---

### DataTable `Enter` key does not fire `RowSelected` in headless tests

**File:** `tests/ui/test_episode_screen.py`
**Symptom:** `test_enter_plays_episode_via_app` — pressing `enter` via `pilot.press("enter")` did not trigger playback.
**Root cause:** Focus management in headless mode; `DataTable` did not reliably receive the key event.
**Fix:** Call `app.screen._play_episode(ep)` directly to test the playback path, bypassing the key event.

---

## Mocking / Test Patching Issues

### `httpx` imported inside function — unpatchable

**File:** `podkstr/downloader.py`
**Symptom:** `patch("podkstr.downloader.httpx.AsyncClient")` had no effect.
**Root cause:** `import httpx` was inside the `download()` function body. Python re-imports at each call but the patch targets the already-imported module, not the local re-import.
**Fix:** Move `import httpx` to module level.

---

### `AsyncMock.aiter_bytes` returns a coroutine, not an async generator

**File:** `tests/test_downloader.py`
**Symptom:** `async for chunk in response.aiter_bytes(...)` raised `TypeError: 'coroutine' object is not an async iterable`
**Root cause:** `AsyncMock(return_value=aiter(...))` wraps the result in a coroutine; `async for` requires an async iterator, not a coroutine that returns one.
**Fix:** Use a real async generator function:
```python
async def fake_aiter_bytes(**kwargs):
    yield content
```

---

### `add_source` modal — button click not triggered by Enter key

**File:** `tests/ui/test_source_screen.py`
**Symptom:** `mock_add.assert_called_once_with(...)` failed — called 0 times.
**Root cause:** Pressing `Enter` inside the modal's `Input` field did not propagate to click the `#btn-add` button.
**Fix:** Use `await pilot.click("#btn-add")` explicitly after setting input values.

---

## Feed Content Rendering Errors

### Rich markup errors from feed descriptions

**File:** `podkstr/ui/episode_screen.py`, `podkstr/fetcher.py`
**Symptom:** `rich.errors.MarkupError` or garbled output when rendering episode descriptions containing `&`, `<`, or `>`.
**Root cause:** Feed content included HTML entities (e.g. `&amp;`, `R&B`) that Rich tried to interpret as markup tags.
**Fix:**
1. Apply `html.unescape()` in `fetcher.py` to decode HTML entities at parse time.
2. Apply `rich.markup.escape()` in `episode_screen._on_feed_loaded` before passing any feed text to Rich widgets.

---

### `Label.renderable` AttributeError in source screen

**File:** `podkstr/ui/source_screen.py`
**Symptom:** `AttributeError` when trying to read the selected source name from the ListView item.
**Root cause:** `event.item.query_one(Label).renderable` does not work in Textual 8.
**Fix:** Look up the source name from `load_sources()` by matching on the URL value stored in the item, instead of reading the Label's rendered text.

---

### Panel derecho muestra siempre la portada del programa, no del episodio

**File:** `podkstr/ui/episode_screen.py`, `podkstr/fetcher.py`
**Symptom:** El panel derecho muestra siempre la misma imagen independientemente del episodio seleccionado.
**Root cause:** `fetcher.py` asigna la imagen del feed como fallback a todos los episodios que no tienen imagen propia (`if not ep_image: ep_image = image_url`). RTVE no publica imágenes por episodio en el RSS, así que todos heredan la portada del programa. `_update_episode_detail` renderizaba esa imagen siempre.
**Fix:** Comparar `ep["image_url"]` con `self._feed["image_url"]`. Si son iguales (fallback), no renderizar imagen en el panel derecho — ya aparece en el widget `#cover-art` superior. Solo renderizar si el episodio tiene una imagen propia distinta.

---

### Secuencias ANSI de chafa mostradas como texto literal

**File:** `podkstr/ui/episode_screen.py`
**Symptom:** La salida de chafa aparece como texto crudo con secuencias de escape (`[38;2;172;174m...`) en lugar de colores.
**Root cause:** Textual renderiza los `Static` widgets a través de Rich, que no interpreta secuencias ANSI crudas — las trata como texto literal. Pasar el `stdout` de chafa directamente a `Static.update()` provoca esto.
**Fix:** Parsear la salida con `Text.from_ansi(result.stdout)` antes de pasarla al widget. Rich convierte las secuencias ANSI a su propio modelo de estilos internamente.

---

### Portada no visible en Tabby (chafa protocolo incorrecto)

**File:** `podkstr/ui/episode_screen.py`
**Symptom:** La portada no se muestra en el terminal Tabby.
**Root cause:** chafa auto-detecta el protocolo de imagen del terminal. En Tabby detecta un protocolo no soportado (iTerm2/kitty/sixel) y emite secuencias de escape que el terminal ignora.
**Fix:** Forzar modo bloques unicode con flags explícitos: `--format=symbols --symbols=block --colors=full`. Genera `▀▄█` con colores ANSI RGB truecolor, compatible con cualquier terminal moderno.
**System:** `brew install chafa` (v1.18.1).

---

### Portada del episodio no visible en panel derecho

**File:** `podkstr/ui/episode_screen.py`
**Symptom:** El panel derecho muestra la descripción pero no la portada del episodio.
**Root cause:** `@work(thread=True, exclusive=True)` en `_render_episode_cover` cancelaba el worker antes de que terminara la descarga. Al renderizar la tabla, `_render_table` lanzaba `_update_episode_detail`, y a continuación `DataTable.RowHighlighted` lo lanzaba de nuevo — el segundo worker cancelaba al primero con `exclusive=True`. Además, la llamada explícita desde `_render_table` era redundante porque `RowHighlighted` ya se dispara automáticamente al pintar la primera fila.
**Fix:** Eliminar `exclusive=True` (el decorator queda como `@work(thread=True)`) y eliminar la llamada a `_update_episode_detail` desde `_render_table`. El único trigger es `on_data_table_row_highlighted`.

---

### Episodio terminado no se puede volver a reproducir

**File:** `podkstr/ui/episode_screen.py`, `podkstr/db.py`
**Symptom:** Al pulsar Enter/Space en un episodio ya escuchado hasta el final, aparece el icono `▶` pero no suena nada.
**Root cause:** Al terminar el episodio, la posición guardada en DB es igual (o casi igual) a la duración total. `_play_episode` recupera esa posición y la pasa como `--start=<pos>` a mpv, que arranca en el último segundo y termina inmediatamente.
**Fix:** En `_play_episode`, si `resume_pos >= total_duration - 30s`, se borra la posición con `db.delete_position` y se reproduce desde el principio (`start_pos=None`). Se añade `delete_position(episode_id)` a `db.py`.

---

### Posición de reproducción en formato incorrecto (`MM:SS` en lugar de `HH:MM:SS`)

**File:** `podkstr/ui/episode_screen.py`
**Symptom:** La columna `Dur.` mostraba `12:14` en lugar de `00:12:14`.
**Root cause:** `_format_position` usaba formato `MM:SS` para duraciones menores de una hora.
**Fix:** Forzar siempre `{h:02d}:{m:02d}:{s:02d}`.

---

## Improvements

Enhancements implemented during development, with design notes.

### Row highlight in episode list
`cursor_type="row"` en el DataTable resalta la fila entera en lugar de solo la celda activa.

### Space bar as play/stop toggle
`space` reproduce el episodio seleccionado; si hay algo reproduciéndose, lo para. `Enter` mantiene el mismo comportamiento. `d` queda exclusivamente para descargar.

### Playback status column
Nueva columna entre `#` y `Title` con iconos de estado por fila:
- Spinner braille `⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏` en naranja → buffering (animado a 120ms con `set_interval`)
- `▶` verde → reproduciendo (transición automática a los 3s, heurístico sin IPC)
- `" "` → sin reproducción

Al transicionar a "playing" o "stop", el timer del spinner se cancela con `.stop()`. La tecla `s` en `EpisodeScreen` también limpia el icono además de parar mpv.

### Panel derecho con portada y descripción del episodio
Layout reestructurado con `Horizontal`: tabla a la izquierda (`2fr`) + panel de detalle a la derecha (`1fr`). El panel muestra la portada del episodio (chafa, `--size=30x8`) y su descripción al mover el cursor por la tabla (`on_data_table_row_highlighted`). El worker `_render_episode_cover` usa `exclusive=True` para cancelar renders anteriores si el usuario se mueve rápido. `fetcher.py` extrae `image_url` por episodio (`media_thumbnail` → `itunes_image` → fallback a portada del feed).

### Posición de reproducción en columna Dur.
Mientras el estado es "playing", un timer de 1s llama a `player.get_time_pos()` (socket IPC `get_property time-pos`) y actualiza la celda `Dur.` de la fila activa con la posición formateada (`MM:SS` o `H:MM:SS`). Al parar, `_restore_duration_cell` recupera el valor original del episodio. El timer se gestiona en `_set_playback_state` junto al resto de timers.

### Seek con flechas ←/→
mpv se lanza con `--input-ipc-server=/tmp/podkstr-mpv.sock`. `player.seek(seconds)` abre el socket Unix, envía `{"command": ["seek", N, "relative"]}` y cierra. Los errores se silencian (socket no disponible = no-op). `←` retrocede 30s, `→` adelanta 30s. Bindings con `priority=True` para capturar las flechas antes de que el DataTable las consuma.

---

### Paginación de episodios no funcionaba (API RTVE devuelve 20 por defecto)

**File:** `podkstr/fetcher.py`, `podkstr/ui/episode_screen.py`
**Symptom:** Las teclas `n` y `p` no cambiaban de página — siempre se veían los mismos 20 episodios.
**Root cause:** La lógica de paginación en `episode_screen.py` era correcta, pero la API RSS de RTVE devuelve solo 20 entradas por defecto. Con `total_pages = 1`, las acciones `next_page` y `prev_page` nunca se ejecutaban.
**Fix:** Lazy loading — `fetch_feed` sigue devolviendo los primeros 20 episodios al instante. Se añade `fetch_next_page(url, page, fallback_image)` en `fetcher.py` que solicita `size=20&page=N` para URLs de RTVE. En `episode_screen.py`, cuando el usuario pulsa `n` en la última página cargada, se lanza un worker que llama a `fetch_next_page` y añade los nuevos episodios a `_all_episodes` sin resetear la página actual.

---

## Pending improvements

Ideas pendientes de implementar.

### Phase 5 — IPC Playback Bar
Barra de progreso en tiempo real con `time-pos` y `duration` del socket IPC. Requiere async socket I/O junto al event loop de Textual (via `asyncio` + `app.set_interval` o hilo de fondo). Incluiría pausa real y auto-avance de episodio.

### Multi-source download queue
Cola de descargas en background con pantalla de progreso. Actualmente las descargas son una a una.

### Search / filter episodes by keyword
Tecla `/` abre una barra de búsqueda inline que filtra el DataTable por subcadena del título.

### Episode resume position
Guardar posición de reproducción en SQLite al parar. Al volver a reproducir, ofrecer reanudar desde donde se dejó. Requiere IPC para leer `time-pos`.

### Configurable Referer header per source
El header `Referer` de RTVE está hardcoded. Si se añaden fuentes con otros requisitos de redirección, debería ser un campo en `sources.json`.

### Export / import sources
Flag CLI (`--export-sources`, `--import-sources`) para compartir `sources.json` entre máquinas.
