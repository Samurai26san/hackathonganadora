# Skills y herramientas del proyecto

La integración conserva `agents/` como fuente y registra sus paquetes en
`.agents/skills/`. No modifica el código ni las dependencias de la aplicación.
El [catálogo](AGENT_CATALOG.md) enumera las skills; el
[inventario JSON](../.agents/catalog.json) incluye las descripciones, fuentes,
copias idénticas y scripts auxiliares.

## Instalación y mantenimiento

Requisitos: Python 3.11+, `uv`, Node.js/npm y Flutter en `PATH`, con una versión
de Dart compatible con la restricción de `pubspec.yaml` (actualmente `^3.13.5`).

```bash
make agents-setup
make agents-doctor
make check
```

La instalación Python usa exclusivamente `.agents/.venv/` y la copia local de
Graphify 0.9.92. `agents-setup` se puede repetir. Los paquetes npm de los MCP se
descargan en la caché de npm al iniciar cada servidor por primera vez; sus
versiones están fijadas en `tools/agents.py`.

Tras añadir o cambiar skills en las colecciones, ejecuta `make agents-sync`.
El registro comprueba el contenido de cada carpeta para deduplicar solamente
paquetes idénticos. Agent Skills 0.6.13 se registra primero y las variantes de
0.6.10 reciben `-original`. Las distribuciones de OpenClaw y del CLI de UI/UX
usan sus skills canónicas sin registrar otro adaptador de plataforma.

Los enlaces son relativos y se pueden versionar junto con las fuentes. Si mueves
el proyecto, ejecuta `make agents-setup` para recrear el entorno Python y
`make agents-config` para regenerar las rutas absolutas de los MCP. La
configuración propia de Codex debe quedar fuera del bloque generado
`project-agent-tools` de `.codex/config.toml`.

## Uso desde Codex

Abre Codex desde la raíz del proyecto. Las skills registradas estarán disponibles
en el siguiente turno; si no aparecen, reinicia la sesión. Ejemplos:

```text
Usa $flutter-expert para implementar esta pantalla.
Usa $ui-ux-pro-max para revisar navegación y accesibilidad.
Usa $code-review-and-quality para revisar estos cambios.
```

El descubrimiento mediante `.agents/skills/` y los enlaces simbólicos está
documentado en la [guía oficial de skills](https://learn.chatgpt.com/docs/build-skills).
La [guía oficial de MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
describe la configuración por proyecto en `.codex/config.toml`. Codex carga
esta configuración en proyectos de confianza. No se modifican las preferencias
globales del usuario; la disponibilidad de los MCP se comprueba en `/mcp` al
abrir una nueva sesión.

## Herramientas

| Herramienta | Entrada | Alcance |
| --- | --- | --- |
| UI/UX Pro Max | `python3 tools/agents.py ui "navigation" --stack flutter` | Búsqueda local en datos de diseño, sin dependencias Python externas |
| Graphify CLI | `python3 tools/agents.py graphify --help` | Análisis y consultas del código |
| Grafo de la app | `make agents-graph` | Código local, sin extracción semántica con LLM |
| Graphify MCP | `.codex/config.toml` | Consultas sobre `graphify-out/graph.json` |
| Playwright MCP | `.codex/config.toml` | Automatización de Flutter web con navegador aislado |
| Chrome DevTools MCP | `.codex/config.toml` | Inspección, rendimiento y depuración de Flutter web |
| shadcn MCP | `.codex/config.toml` | Herramienta incluida por la colección UI/UX para proyectos web compatibles |
| Otros scripts | `.agents/catalog.json`, campo `tools` | Utilidades de las colecciones, con su runtime identificado |

Puedes invocar cualquier script inventariado por su ruta original usando
Python, Node o Bash según el campo `runtime`. Los scripts TypeScript requieren
el entorno de su paquete. El catálogo no ejecuta instaladores, hooks ni scripts
de publicación automáticamente. Las funciones que generan imágenes o usan
proveedores externos conservan los requisitos y credenciales de su colección.
Ponytail se integra mediante sus seis skills; sus hooks específicos de otros
hosts permanecen en la colección y no se registran como hooks de Codex.

Para arrancar la app web y usar las herramientas del navegador:

```bash
flutter run -d web-server --web-port 8080
```

Playwright puede necesitar descargar su navegador la primera vez. Si lo indica,
usa `browser_install` de su MCP. Chrome DevTools necesita Chrome/Chromium
disponible. El registro y la conexión MCP no equivalen a una prueba de interfaz.

Graphify reconoce Dart mediante extracción basada en expresiones regulares;
su grafo es una ayuda de navegación, no un análisis completo del lenguaje.
Los archivos generados del grafo y el entorno Python se excluyen de Git.
