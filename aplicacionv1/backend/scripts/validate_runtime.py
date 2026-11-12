"""Opt-in real localhost validation. No mocked OIDC provider, model or embeddings."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from contextlib import closing
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[2]
BASE = "http://localhost:8080"
RESULTS: list[dict[str, object]] = []


class LoginForm(HTMLParser):
    action = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "form" and attributes.get("id") == "kc-form-login":
            self.action = attributes.get("action") or ""


def check(name: str, condition: bool, started: float | None = None) -> None:
    result: dict[str, object] = {"check": name, "passed": bool(condition)}
    if started is not None:
        result["seconds"] = round(time.monotonic() - started, 3)
    RESULTS.append(result)
    print(f'{"OK" if condition else "FAIL"}: {name}', flush=True)
    if not condition:
        raise AssertionError(name)


def login(email: str, expect_status: int = 303) -> httpx.Client:
    client = httpx.Client(base_url=BASE, timeout=180, follow_redirects=False)
    response = client.post("/api/v1/auth/login", json={})
    check("OIDC autorización solicitada", response.status_code == 200)
    authorization = response.json()["authorization_url"]
    parsed = urlsplit(authorization)
    check(
        "Proveedor local y PKCE S256",
        parsed.netloc == "localhost:8180"
        and "code_challenge_method=S256" in parsed.query,
    )
    page = client.get(authorization)
    form = LoginForm()
    form.feed(page.text)
    check("Formulario real de Keycloak", bool(form.action))
    target = urlsplit(form.action)
    check(
        "Formulario limitado al realm local",
        target.netloc == "localhost:8180"
        and target.path.startswith("/realms/exb-local/"),
    )
    # Chromium sends Keycloak's Secure cookies on trusted localhost HTTP.
    # httpx does not implement that browser exception. Emulate it only for this
    # explicit local fixture, preserving actual cookie flags and server behavior.
    provider_cookies = "; ".join(
        f"{cookie.name}={cookie.value}"
        for cookie in client.cookies.jar
        if cookie.domain in {"localhost", "localhost.local"}
        and cookie.path.startswith("/realms/exb-local/")
    )
    response = client.post(
        form.action,
        data={"username": email, "password": "Demo2026!", "credentialId": ""},
        headers={"Cookie": provider_cookies},
    )
    check(
        "Keycloak emite código de autorización",
        response.status_code == 302
        and "/auth/callback?" in response.headers.get("location", ""),
    )
    callback = response.headers["location"]
    response = client.get(callback)
    check(f"Callback para cuenta {email}", response.status_code == expect_status)
    if expect_status == 303:
        check(
            "Cookie HttpOnly SameSite=Lax",
            any(
                "HttpOnly" in value and "SameSite=lax" in value
                for value in response.headers.get_list("set-cookie")
            ),
        )
    return client


def identity() -> None:
    started = time.monotonic()
    with closing(login("sin-acceso@exb.demo", 403)) as denied:
        check(
            "Cuenta no provisionada sin sesión",
            denied.get("/api/v1/auth/me").status_code == 401,
        )
    with closing(login("tecnico@exb.demo")) as technician:
        check(
            "Rol de aplicación conservado",
            technician.get("/api/v1/auth/me").json()["role"] != "admin",
        )
        check(
            "Técnico sin acceso a usuarios",
            technician.get("/api/v1/users").status_code == 403,
        )
    with closing(login("admin@exb.demo")) as admin:
        check(
            "Administración provisionada",
            admin.get("/api/v1/auth/me").json()["role"] == "admin",
        )
        old_cookies = dict(admin.cookies)
        check(
            "Rotación de sesión", admin.post("/api/v1/auth/refresh").status_code == 200
        )
        with httpx.Client(base_url=BASE, cookies=old_cookies) as previous:
            check(
                "Cookie previa revocada",
                previous.get("/api/v1/auth/me").status_code == 401,
            )
        check(
            "Origen ajeno denegado",
            admin.post(
                "/api/v1/auth/refresh",
                headers={"Origin": "https://no-autorizado.example"},
            ).status_code
            == 403,
        )
        check("Cierre de sesión", admin.post("/api/v1/auth/logout").status_code == 200)
        check(
            "Sesión cerrada revocada", admin.get("/api/v1/auth/me").status_code == 401
        )
    check("Flujo OIDC completo real", True, started)


def conversation(
    client: httpx.Client, message: str, session_id: str | None = None
) -> list[dict]:
    started = time.monotonic()
    response = client.post(
        "/api/v1/chat/stream", json={"message": message, "session_id": session_id}
    )
    check("SSE HTTP disponible", response.status_code == 200)
    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    errors = [event for event in events if event["event"] == "error"]
    check(
        "Conversación real completada sin error",
        not errors and any(e["event"] == "done" for e in events),
        started,
    )
    return events


def finance(admin: httpx.Client) -> tuple[dict, dict]:
    catalog = admin.get("/api/v1/catalogs").json()
    check("Solo gestiones reales disponibles", catalog["years"] == [2026])
    reference = admin.get("/api/v1/budget/execution/summary?years=2026").json()
    summary = reference["summary"]
    check(
        "Reconciliación con Excel real",
        summary["current_budget"] == "3163379.01"
        and summary["executed"] == "528694.16"
        and summary["balance"] == "2634684.85",
    )
    for format_, signature in [("excel", b"PK"), ("pdf", b"%PDF"), ("csv", None)]:
        response = admin.post(
            "/api/v1/reports/export",
            json={
                "report": "summary",
                "format": format_,
                "filters": {"years": [2026]},
            },
        )
        check(
            f"Exportación real {format_}",
            response.status_code == 200
            and len(response.content) > 30
            and (signature is None or response.content.startswith(signature)),
        )
    for report in (
        "account",
        "financier",
        "area",
        "region",
        "monthly",
        "movements",
        "summary",
    ):
        started = time.monotonic()
        response = admin.get(f"/api/v1/budget/execution/{report}?years=2026")
        check(
            f"Informe autorizado {report} concilia",
            response.status_code == 200 and response.json()["summary"] == summary,
            started,
        )
    check(
        "Comparación sin gestión inventada",
        admin.get("/api/v1/budget/compare?years=2025,2026").status_code
        in {400, 404, 422},
    )
    return catalog, summary


def ai() -> None:
    with httpx.Client(timeout=120) as models:
        check(
            "llama.cpp saludable",
            models.get("http://localhost:18081/health").status_code == 200,
        )
        info = models.get("http://localhost:18081/v1/models").json()
        check(
            "Qwen publicado con alias esperado",
            any(m["id"] == "qwen2.5-7b-instruct-q4_k_m" for m in info["data"]),
        )
        started = time.monotonic()
        embedding = models.post(
            "http://localhost:8082/embed",
            json={"inputs": ["Fragmentación de textos en Juku"], "truncate": True},
        ).json()[0]
        check(
            "BGE-m3 real: 1024 componentes finitos",
            len(embedding) == 1024
            and all(math.isfinite(v) for v in embedding)
            and any(embedding),
            started,
        )
    with closing(login("admin@exb.demo")) as admin:
        catalog, summary = finance(admin)
        path = ROOT / "docs/rag_guide.md"
        content = path.read_text()
        started = time.monotonic()
        response = admin.post(
            "/api/v1/knowledge/ingest",
            json={
                "content": content,
                "source_type": "manual",
                "source_id": "project:docs/rag_guide.md",
                "source_title": "Guía de conocimiento de Juku (documentación del proyecto)",
                "tags": ["documentacion_proyecto"],
                "metadata": {
                    "path": "docs/rag_guide.md",
                    "sha256": hashlib.sha256(content.encode()).hexdigest(),
                    "scope": "manual de aplicación; no es normativa legal",
                },
            },
        )
        check(
            "Ingesta real de documentación existente",
            response.status_code == 200 and response.json()["chunks"] > 0,
            started,
        )
        started = time.monotonic()
        hits = admin.post(
            "/api/v1/knowledge/search",
            json={
                "query": "¿Cómo se fragmenta el texto por tokens con solapamiento en Juku?",
                "source_types": ["manual"],
            },
        ).json()["results"]
        check(
            "Recuperación semántica con procedencia",
            any(hit["source_id"] == "project:docs/rag_guide.md" for hit in hits),
            started,
        )
        no_laws = admin.post(
            "/api/v1/knowledge/search",
            json={"query": "¿Qué leyes hay cargadas?", "source_types": ["law"]},
        ).json()["results"]
        check("Ausencia de leyes sin citas fabricadas", no_laws == [])
        events = conversation(
            admin,
            "Dame el resumen general de presupuesto, ejecutado y saldo de la gestión 2026.",
        )
        financial = [
            e["data"]["result"]
            for e in events
            if e["event"] == "tool_result"
            and not e["data"]["is_error"]
            and "summary" in e["data"]["result"]
        ]
        check(
            "Qwen invoca motor financiero y conserva centavos",
            bool(financial) and financial[-1]["summary"] == summary,
        )
        session_id = events[-1]["session_id"]
        events = conversation(
            admin, "Ahora muéstralo por región, conserva la gestión.", session_id
        )
        check(
            "Cambio de informe conserva contexto",
            any(
                e["event"] == "context_update"
                and e["data"]["current_report"] == "region"
                and e["data"]["active_filters"]["years"] == [2026]
                for e in events
            ),
        )
        region = catalog["region"][0]
        events = conversation(
            admin, f'Filtra solo la región {region["name"]}.', session_id
        )
        check(
            "Tercer turno conserva filtro regional",
            any(
                e["event"] == "context_update"
                and e["data"]["active_filters"]["region_ids"] == [region["id"]]
                for e in events
            ),
        )
        regional_account = next(
            (
                u
                for u in admin.get("/api/v1/users").json()
                if u["email"] == "regional@exb.demo"
            ),
            None,
        )
        local_account = {
            "email": "regional@exb.demo",
            "full_name": "Validación regional local",
            "role": "viewer",
            "region_ids": [region["id"]],
            "area_ids": None,
            "financier_ids": None,
            "is_active": True,
        }
        response = (
            admin.put(f'/api/v1/users/{regional_account["id"]}', json=local_account)
            if regional_account
            else admin.post("/api/v1/users", json=local_account)
        )
        check("Cuenta local con alcance explícito", response.status_code == 200)
        expected = admin.get(
            "/api/v1/budget/execution/summary",
            params={"years": 2026, "region_ids": region["id"]},
        ).json()["summary"]
        with closing(login("regional@exb.demo")) as scoped:
            check(
                "Catálogo real restringido por región",
                scoped.get("/api/v1/catalogs").json()["region"] == [region],
            )
            check(
                "Informe real aplica alcance del servidor",
                scoped.get("/api/v1/budget/execution/summary?years=2026").json()[
                    "summary"
                ]
                == expected,
            )
            restricted_events = conversation(
                scoped,
                "Dame el resumen general de 2026 para todas las regiones disponibles.",
            )
            allowed = [
                e["data"]["result"]["summary"]
                for e in restricted_events
                if e["event"] == "tool_result"
                and not e["data"]["is_error"]
                and "summary" in e["data"]["result"]
            ]
            check(
                "Consulta Qwen respeta alcance regional",
                bool(allowed) and allowed[-1] == expected,
            )
        with closing(login("tecnico@exb.demo")) as technician:
            check(
                "Historial aislado entre cuentas",
                technician.get(f"/api/v1/sessions/{session_id}/messages").status_code
                == 404,
            )
        events = conversation(
            admin,
            "Según la guía de conocimiento de Juku, ¿cómo se fragmentan los textos por tokens y qué solapamiento usan? Consulta el manual cargado.",
        )
        citations = [
            c
            for e in events
            if e["event"] == "tool_result" and not e["data"]["is_error"]
            for c in e["data"]["result"].get("citations", [])
        ]
        check(
            "Juku cita el manual real recuperado",
            any(c["source_id"] == "project:docs/rag_guide.md" for c in citations)
            and "[Fuente " in str(events[-1]["data"]),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase", choices=["oidc", "finance", "ai", "all"], default="oidc"
    )
    args = parser.parse_args()
    error = None
    try:
        if args.phase in {"oidc", "all"}:
            identity()
        if args.phase == "finance":
            with closing(login("admin@exb.demo")) as admin:
                finance(admin)
        if args.phase in {"ai", "all"}:
            ai()
    except Exception as exception:
        # Never print redirect URLs, authorization codes, cookies or tokens.
        error = type(exception).__name__
        print(f"Validación detenida: {error}", flush=True)
    report = {
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "phase": args.phase,
        "passed": error is None,
        "error_type": error,
        "checks": RESULTS,
    }
    path = ROOT / f"docs/validation_{args.phase}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if error:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
