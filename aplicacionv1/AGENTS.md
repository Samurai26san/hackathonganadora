# Agentes para aplicacionv1

Este proyecto es una aplicación Flutter/Dart. El código de la aplicación está en
`lib/`, las pruebas en `test/` y las dependencias en `pubspec.yaml`.
Responde en español salvo que el usuario solicite otro idioma.

## Skills y herramientas locales

Las colecciones originales se conservan en `agents/`. Las skills se descubren en
`.agents/skills/` mediante enlaces relativos que incluyen scripts, referencias y
assets. Consulta `docs/AGENT_CATALOG.md` o busca en `.agents/catalog.json` para
encontrar una skill; lee su `SKILL.md` cuando sea pertinente a la tarea. Carga
solamente los recursos necesarios para el trabajo actual.

Para tareas de este proyecto, empieza por estas especialidades cuando apliquen:

| Trabajo | Skills |
| --- | --- |
| Flutter, Dart, widgets y plataformas | `flutter-expert`, `mobile-developer` |
| Diseño visual, interacción y accesibilidad | `ui-ux-pro-max`, `ui-ux-designer`, `wcag-audit-patterns` |
| Requisitos e implementación | `spec-driven-development`, `incremental-implementation` |
| Errores y pruebas | `debugging-and-error-recovery`, `test-driven-development` |
| Revisión y seguridad móvil | `code-review-and-quality`, `mobile-security-coder` |
| Arquitectura y relaciones del código | `architecture-patterns`, `graphify` |
| Simplificación | `code-simplification`, `ponytail` |

La colección Agent Skills 0.6.13 tiene prioridad sobre 0.6.10. Las variantes
distintas se conservan con el sufijo `-original`; las copias idénticas comparten
un registro. Las distribuciones para OpenClaw y el instalador de UI/UX conservan
sus fuentes, pero se usa la skill canónica de cada paquete.

Resuelve las rutas de recursos respecto al directorio original de cada skill
(`readlink -f .agents/skills/<nombre>`), especialmente cuando una referencia
apunte fuera de su carpeta. Los `AGENTS.md` internos de las colecciones describen
el mantenimiento de esos repositorios; su alcance no se extiende a la app.
Las indicaciones de frameworks distintos se adaptan a Flutter cuando proceda.

## Comandos

```bash
make agents-setup        # Instalar Graphify y registrar skills y MCP locales
make agents-sync         # Actualizar skills y catálogo tras cambiar agents/
make agents-config       # Regenerar rutas MCP al mover o clonar el proyecto
make agents-check        # Validar nombres, fuentes, adaptadores y enlaces
make agents-doctor       # Comprobar runtimes y herramientas disponibles
make agents-test         # Probar el registro y la preservación de archivos
make agents-graph        # Crear/actualizar el grafo del código, sin usar un LLM
make check               # Validar integración y ejecutar analyze/test de Flutter
```

Consulta la base de diseño con:

```bash
python3 tools/agents.py ui "navigation accessibility" --stack flutter
```

Graphify usa `.agents/.venv/`. Su entrada CLI es
`python3 tools/agents.py graphify <argumentos>`. Si existe un grafo del proyecto,
puede usarse para orientar consultas de arquitectura; contrasta los resultados
con el código. Después de cambios relevantes, `make agents-graph` lo actualiza.
El análisis excluye las colecciones y dependencias de agentes. La extracción
de Dart de esta versión usa expresiones regulares y puede omitir relaciones.

Los servidores MCP de `.codex/config.toml` son Graphify, Playwright,
Chrome DevTools y shadcn. Los tres últimos proceden de la configuración incluida
en UI/UX Pro Max y tienen versiones fijadas. Playwright/Chrome se usan para
Flutter web; shadcn se reserva para tareas web que realmente usen ese ecosistema.
Para conectar los servidores, abre una sesión de Codex desde este proyecto
con su configuración local habilitada. Detalles en `docs/AGENTS_SETUP.md`.

El catálogo de scripts incluye utilidades de mantenimiento, publicación y
generación; lee su propósito y dependencias antes de ejecutarlas. Instalar una
skill no concede acceso a servicios externos ni instala todas sus dependencias
opcionales. Ejecuta las comprobaciones proporcionales al cambio y evita añadir
dependencias de otros stacks a `pubspec.yaml` por registrar estas herramientas.

## Continuidad solicitada por el usuario

Avanza por pasos verificables. Antes de trabajar, lee `tasks/PROGRESS.md` y
`tasks/todo.md`. Al terminar cada paso, registra qué cambió, la comprobación
realizada, su resultado y el siguiente paso exacto. Si se interrumpe la sesión,
retoma el primer paso pendiente desde el último punto verificado; conserva el
código existente y no repitas pasos completados salvo que un cambio los afecte.
Los procesos locales pueden detenerse entre sesiones: comprueba sus puertos y
su identidad antes de reiniciarlos. No confundas configuración preparada con
servicios externos o modelos realmente validados.
