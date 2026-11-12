#!/usr/bin/env python3
"""Register the bundled skills without modifying their source collections."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.agents'
SOURCES = (
    'agents/skills',
    'agents/agent-skills-main (2)/skills',
    'agents/agent-skills-main/skills',
    'agents/ponytail-main/skills',
    'agents/ui-ux-pro-max-skill-main/.claude/skills',
)
SKIP = {'__pycache__', 'node_modules', '.git', 'tests', 'test', 'fixtures', 'evals'}
MCP_PACKAGES = {
    'playwright': ['@playwright/mcp@0.0.85', '--headless', '--isolated'],
    'chrome-devtools': ['chrome-devtools-mcp@1.13.0', '--headless', '--isolated', '--no-usage-statistics'],
    'shadcn': ['shadcn@4.23.0', 'mcp'],
}


def metadata(path):
    import yaml
    text = path.read_text(encoding='utf-8')
    if not text.startswith('---\n'):
        raise ValueError(f'Falta frontmatter: {path}')
    data = yaml.safe_load(text.split('---', 2)[1])
    if not isinstance(data, dict):
        raise ValueError(f'Frontmatter inválido: {path}')
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', data.get('name', '')):
        raise ValueError(f'Nombre inválido: {path}')
    if not isinstance(data.get('description'), str) or not data['description'].strip():
        raise ValueError(f'Descripción inválida: {path}')
    return data


def fingerprint(folder):
    digest = hashlib.sha256()
    for path in sorted(folder.rglob('*')):
        relative = path.relative_to(folder)
        if path.is_file() and not SKIP.intersection(relative.parts) and path.suffix != '.pyc':
            digest.update(str(relative).encode())
            digest.update(b'\0')
            digest.update(path.read_bytes())
    return digest.hexdigest()


def discover():
    records, by_name = [], {}
    for source in SOURCES:
        if not (ROOT / source).is_dir():
            raise ValueError(f'Colección ausente: {source}')
        for manifest in sorted((ROOT / source).glob('*/SKILL.md')):
            data = metadata(manifest)
            name = data['name']
            digest = fingerprint(manifest.parent)
            versions = by_name.setdefault(name, [])
            same = next((v for v in versions if v['sha256'] == digest), None)
            relative = str(manifest.parent.relative_to(ROOT))
            if same:
                same['duplicates'].append(relative)
                continue
            installed_name = name if not versions else f'{name}-original'
            if any(r['name'] == installed_name for r in records):
                raise ValueError(f'Colisión de nombres: {installed_name}')
            record = dict(name=installed_name, source=relative, sha256=digest,
                          description=data['description'].strip(), duplicates=[])
            records.append(record)
            versions.append(record)
    manifest = ROOT / 'agents/graphify-8/graphify/skill-codex.md'
    data = metadata(manifest)
    records.append(dict(name=data['name'], source=str(manifest.relative_to(ROOT)),
                        sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
                        description=data['description'], duplicates=[]))
    return sorted(records, key=lambda record: record['name'])


def link(source, destination):
    if destination.is_symlink() and destination.resolve() == source.resolve():
        return
    if destination.exists() or destination.is_symlink():
        raise ValueError(f'No se sobrescribirá el archivo existente: {destination}')
    destination.symlink_to(os.path.relpath(source, destination.parent),
                           target_is_directory=source.is_dir())


def tool_inventory():
    tools = []
    interpreters = {'.py': 'python3', '.sh': 'bash', '.js': 'node',
                    '.cjs': 'node', '.mjs': 'node', '.ts': 'typescript'}
    for path in sorted((ROOT / 'agents').rglob('*')):
        relative = path.relative_to(ROOT)
        if (path.is_file() and 'scripts' in relative.parts
                and not SKIP.intersection(relative.parts)
                and path.suffix in interpreters
                and not re.search(r'(?:^|[._-])test(?:[._-]|$)', path.name)):
            tools.append(dict(path=str(relative), runtime=interpreters[path.suffix]))
    return tools


def sync():
    records = discover()
    installed = STATE / 'skills'
    installed.mkdir(parents=True, exist_ok=True)
    # Preflight every destination before writing any generated adapter.
    for record in records:
        target = installed / record['name']
        source = ROOT / record['source']
        if target.exists() or target.is_symlink():
            if source.is_dir() and record['name'] == metadata(source / 'SKILL.md')['name']:
                if not target.is_symlink() or target.resolve() != source.resolve():
                    raise ValueError(f'Destino ocupado: {target}')
            elif not (target / '.generated-by-agents').is_file():
                raise ValueError(f'Destino ocupado: {target}')
    for record in records:
        source = ROOT / record['source']
        target = installed / record['name']
        if source.is_dir() and record['name'] == metadata(source / 'SKILL.md')['name']:
            link(source, target)
            continue
        target.mkdir(exist_ok=True)
        (target / '.generated-by-agents').write_text('tools/agents.py\n', encoding='utf-8')
        if source.is_file():
            link(source, target / 'SKILL.md')
            link(source.parent / 'skills/codex/references', target / 'references')
        else:
            text = (source / 'SKILL.md').read_text(encoding='utf-8')
            text = re.sub(r'^name:.*$', f'name: {record["name"]}', text, count=1, flags=re.M)
            (target / 'SKILL.md').write_text(text, encoding='utf-8')
            for child in source.iterdir():
                if child.name != 'SKILL.md' and child.name not in SKIP:
                    link(child, target / child.name)
    catalog = dict(skills=records, tools=tool_inventory(),
                   distribution_copies=['agents/ponytail-main/.openclaw/skills',
                                        'agents/ui-ux-pro-max-skill-main/cli/assets/skills'])
    (STATE / 'catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    rows = ['# Catálogo de agentes', '',
            'Generado con `python3 tools/agents.py sync`. Las fuentes se conservan en `agents/`.', '',
            f'{len(records)} skills registradas; {len(catalog["tools"])} scripts auxiliares inventariados.', '',
            'La versión de Agent Skills 0.6.13 tiene prioridad. Las variantes distintas de 0.6.10',
            'llevan el sufijo `-original`. Las copias de distribución de OpenClaw y del CLI de UI/UX',
            'permanecen en sus fuentes; se registra la versión canónica de cada paquete.', '',
            'El inventario completo de scripts está en [catalog.json](../.agents/catalog.json).',
            'Que un script esté inventariado no implica que sus dependencias opcionales estén instaladas.', '',
            '| Skill | Fuente | Copias idénticas |', '| --- | --- | --- |']
    for record in records:
        source = record['source']
        manifest = source if source.endswith('.md') else source + '/SKILL.md'
        rows.append(f'| `{record["name"]}` | [Fuente](<../{manifest}>) | {len(record["duplicates"])} |')
    (ROOT / 'docs/AGENT_CATALOG.md').write_text('\n'.join(rows) + '\n', encoding='utf-8')
    print(f'{len(records)} skills registradas y {len(catalog["tools"])} scripts inventariados.')


def configure_mcp():
    config = ROOT / '.codex/config.toml'
    marker = '# BEGIN project-agent-tools\n'
    end = '# END project-agent-tools\n'
    text = config.read_text(encoding='utf-8') if config.exists() else ''
    unmanaged = text.split(marker, 1)[0] + (text.split(end, 1)[1] if end in text else '')
    if ('project-agent-tools' in text and (text.count(marker) != 1 or text.count(end) != 1)):
        raise ValueError('Bloque MCP incompleto; revisa .codex/config.toml.')
    for name in [*MCP_PACKAGES, 'graphify']:
        if re.search(rf'^\[mcp_servers\.["\']?{re.escape(name)}["\']?\]', unmanaged, re.M):
            raise ValueError(f'Ya existe configuración MCP propia para {name}.')
    lines = [marker.rstrip(), '# Generado con make agents-config. Conserva las opciones propias fuera de este bloque.']
    servers = {name: dict(command='npx', args=['--yes', *args])
               for name, args in MCP_PACKAGES.items()}
    servers['graphify'] = dict(command=str(STATE / '.venv/bin/python'),
                              args=[str(ROOT / 'tools/agents.py'), 'graphify-mcp'])
    for name, server in servers.items():
        lines.extend(['', f'[mcp_servers.{name}]', f'command = {json.dumps(server["command"])}',
                      f'args = {json.dumps(server["args"])}', f'cwd = {json.dumps(str(ROOT))}',
                      'startup_timeout_sec = 120', 'tool_timeout_sec = 120', 'enabled = true'])
    lines.extend(['', end.rstrip(), ''])
    block = '\n'.join(lines)
    config.parent.mkdir(exist_ok=True)
    if marker in text:
        text = text.split(marker, 1)[0] + block + text.split(end, 1)[1]
    else:
        text = text.rstrip() + ('\n\n' if text.strip() else '') + block
    config.write_text(text, encoding='utf-8')
    print('4 servidores MCP configurados para este proyecto.')


def check():
    catalog = json.loads((STATE / 'catalog.json').read_text(encoding='utf-8'))
    if catalog['skills'] != discover() or catalog['tools'] != tool_inventory():
        raise ValueError('Catálogo desactualizado. Ejecuta: python3 tools/agents.py sync')
    seen = set()
    for record in catalog['skills']:
        target = STATE / 'skills' / record['name']
        data = metadata(target / 'SKILL.md')
        if data['name'] != record['name'] or data['name'] in seen:
            raise ValueError(f'Nombre duplicado o incorrecto: {target}')
        seen.add(data['name'])
        source = ROOT / record['source']
        if source.is_dir() and record['name'] == metadata(source / 'SKILL.md')['name']:
            if not target.is_symlink() or target.resolve() != source.resolve():
                raise ValueError(f'Enlace incorrecto: {target}')
        else:
            original = source if source.is_file() else source / 'SKILL.md'
            expected = re.sub(r'^name:.*$', f'name: {record["name"]}', original.read_text(encoding='utf-8'), count=1, flags=re.M)
            if (target / 'SKILL.md').read_text(encoding='utf-8') != expected:
                raise ValueError(f'Adaptador desactualizado: {target}')
        for path in target.rglob('*'):
            if path.is_symlink() and not path.exists():
                raise ValueError(f'Enlace roto: {path}')
    extra = {p.name for p in (STATE / 'skills').iterdir()} - seen
    if extra:
        print('Skills locales adicionales:', ', '.join(sorted(extra)))
    print(f'OK: {len(seen)} skills, nombres únicos, fuentes actuales y recursos enlazados.')


def run(command):
    return subprocess.call([str(part) for part in command], cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['sync', 'check', 'configure-mcp', 'doctor', 'ui', 'graphify', 'graphify-mcp', 'graph-build'])
    # Parse only the dispatch command so delegated --help belongs to that CLI.
    args = parser.parse_args(sys.argv[1:2])
    rest = sys.argv[2:]
    if rest[:1] == ['--']:
        rest = rest[1:]
    if args.command in {'sync', 'check'}:
        if rest:
            parser.error('Este comando no acepta argumentos adicionales.')
        globals()[args.command]()
        return 0
    if args.command == 'configure-mcp':
        configure_mcp()
        return 0
    if args.command == 'doctor':
        check()
        missing = []
        for name in ['python3', 'node', 'npm', 'npx', 'uv', 'flutter', 'dart']:
            location = shutil.which(name)
            print(f'{name}: {location or "NO DISPONIBLE"}')
            if not location:
                missing.append(name)
        executable = STATE / '.venv/bin/graphify'
        print(f'graphify: {executable if executable.exists() else "EJECUTA make agents-setup"}')
        return int(bool(missing) or not executable.exists())
    if args.command == 'ui':
        return run([sys.executable, ROOT / 'agents/ui-ux-pro-max-skill-main/.claude/skills/ui-ux-pro-max/scripts/search.py', *rest])
    python = STATE / '.venv/bin/python'
    if not python.exists():
        raise ValueError('Ejecuta make agents-setup para instalar Graphify en el entorno local.')
    if args.command == 'graphify-mcp':
        return run([python, '-m', 'graphify.serve', '--graph', 'graphify-out/graph.json', *rest])
    if args.command == 'graph-build':
        return run([STATE / '.venv/bin/graphify', 'extract', '.', '--code-only',
                    '--exclude', 'agents/**', '--exclude', '.agents/**',
                    '--exclude', 'build/**', '--exclude', '.dart_tool/**', *rest])
    return run([STATE / '.venv/bin/graphify', *rest])


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)
