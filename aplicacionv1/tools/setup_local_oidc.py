"""Prepare the explicitly local Keycloak fixture without replacing app secrets."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    users = []
    for name in ("admin", "tecnico", "regional", "sin-acceso"):
        users.append(
            {
                "username": f"{name}@exb.demo",
                "email": f"{name}@exb.demo",
                "firstName": name.capitalize(),
                "lastName": "ExB local",
                "enabled": True,
                "emailVerified": True,
                "credentials": [
                    {"type": "password", "value": "Demo2026!", "temporary": False}
                ],
            }
        )
    realm = {
        "realm": "exb-local",
        "enabled": True,
        "sslRequired": "none",
        "registrationAllowed": False,
        "resetPasswordAllowed": False,
        "clients": [
            {
                "clientId": "budget-copilot-web",
                "enabled": True,
                "publicClient": True,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": False,
                "implicitFlowEnabled": False,
                "redirectUris": ["http://localhost:8080/api/v1/auth/callback"],
                "webOrigins": ["http://localhost:8080"],
                "attributes": {"pkce.code.challenge.method": "S256"},
                "defaultClientScopes": ["profile", "email"],
            }
        ],
        "users": users,
    }
    folder = ROOT / "ops/runtime/keycloak"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "exb-local-realm.json").write_text(json.dumps(realm, indent=2) + "\n")
    env = ROOT / ".env"
    if not env.is_file():
        raise SystemExit("Crea .env con SECRET_KEY antes de configurar OIDC local.")
    settings = {
        "APP_ENV": "development",
        "AUTH_MODE": "oidc",
        "COOKIE_SECURE": "false",
        "OIDC_PROVIDER_URL": "http://localhost:8180/realms/exb-local",
        "OIDC_CLIENT_ID": "budget-copilot-web",
        "OIDC_CLIENT_SECRET": "",
        "OIDC_REDIRECT_URI": "http://localhost:8080/api/v1/auth/callback",
        "LLM_SERVER_URL": "http://localhost:18081/v1",
        "EMBEDDINGS_SERVER_URL": "http://localhost:8082",
    }
    lines = []
    for line in env.read_text().splitlines():
        key = line.split("=", 1)[0]
        lines.append(f"{key}={settings.pop(key)}" if key in settings else line)
    lines.extend(f"{key}={value}" for key, value in settings.items())
    env.write_text("\n".join(lines) + "\n")
    print(
        "Realm local generado y .env configurado. Reinicia solo la API de este proyecto."
    )
    print(
        "Cuentas locales: admin@exb.demo, tecnico@exb.demo, sin-acceso@exb.demo (Demo2026!)."
    )


if __name__ == "__main__":
    main()
