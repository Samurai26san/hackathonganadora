"""Predicción de etiquetas faltantes (financiador, rubro, cuenta, área, región).

Modelo: Naive Bayes multinomial por campo, entrenado con las filas completas ya
cargadas en la base (movimientos y presupuesto). Rasgos de cada fila:
  - código de la cuenta contable (p. ej. cc:5102080013) y palabras de su nombre
  - palabras de la glosa / referencia (p. ej. "lp", "catalyst", "alquiler")
  - las demás etiquetas conocidas de la fila (p. ej. cuenta=4.1 Videos ayuda a predecir el rubro)
  - mes y tipo de fila (presupuesto o ejecución)

Es liviano (Python puro), explicable y aprende de cada validación del administrador,
porque las filas validadas pasan a la base y entran al siguiente entrenamiento.
"""
import math
import re
import unicodedata
from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from .models import Area, Cuenta, Financiador, Movimiento, Presupuesto, Region, Rubro

CAMPOS = ["fondo", "rubro", "cuenta", "area", "region"]
ETIQUETAS_CAMPO = {"fondo": "Financiador", "rubro": "Rubro", "cuenta": "Cuenta", "area": "Área", "region": "Región"}
_STOP = {"de", "la", "el", "los", "las", "del", "y", "en", "por", "para", "a", "con", "al", "pago", "lp", "sc"}


def _tokens(texto: str | None) -> list[str]:
    if not texto:
        return []
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return [w for w in re.split(r"[^a-z0-9]+", t) if len(w) > 2 and not w.isdigit() and w not in _STOP]


def rasgos(fila: dict, objetivo: str) -> list[str]:
    """fila: {descripcion, cuenta_contable, mes, tipo, etiquetas: {campo: valor}}"""
    f = [f"tipo:{fila.get('tipo')}", f"mes:{fila.get('mes')}"]
    cc = (fila.get("cuenta_contable") or "").split(" ", 1)
    if cc[0]:
        f.append(f"cc:{cc[0]}")
        f += [f"ccw:{w}" for w in _tokens(cc[1] if len(cc) > 1 else "")]
    desc = fila.get("descripcion") or ""
    # El prefijo de la glosa ("LP.", "SC.") indica la regional que registró
    m = re.match(r"\s*([A-Za-z]{2,3})\.", desc)
    if m:
        f.append(f"pref:{m.group(1).upper()}")
    f += [f"w:{w}" for w in set(_tokens(desc))]
    for campo, valor in (fila.get("etiquetas") or {}).items():
        if campo != objetivo and valor:
            f.append(f"{campo}={valor}")
    return f


class NaiveBayes:
    def __init__(self, alpha: float = 0.5):
        self.alpha = alpha
        self.n_clase = Counter()
        self.cuenta = defaultdict(Counter)
        self.total = Counter()
        self.vocab = set()

    def entrenar(self, ejemplos: list[tuple[list[str], str]]):
        for feats, clase in ejemplos:
            self.n_clase[clase] += 1
            self.cuenta[clase].update(feats)
            self.total[clase] += len(feats)
            self.vocab.update(feats)
        return self

    def predecir(self, feats: list[str], top: int = 3) -> list[tuple[str, float]]:
        if not self.n_clase:
            return []
        n = sum(self.n_clase.values())
        v = len(self.vocab) or 1
        feats = [f for f in feats if f in self.vocab]
        scores = {}
        for c, nc in self.n_clase.items():
            s = math.log(nc / n)
            den = self.total[c] + self.alpha * v
            for f in feats:
                s += math.log((self.cuenta[c][f] + self.alpha) / den)
            scores[c] = s
        # Temperatura para moderar la sobreconfianza típica de Naive Bayes
        temp = max(1.0, len(feats) / 6)
        mx = max(scores.values())
        exp = {c: math.exp((s - mx) / temp) for c, s in scores.items()}
        z = sum(exp.values())
        return sorted(((c, e / z) for c, e in exp.items()), key=lambda x: -x[1])[:top]


def filas_entrenamiento(db: Session) -> list[dict]:
    """Filas completas de la base como ejemplos de entrenamiento."""
    rub = {r.id: r.codigo for r in db.query(Rubro)}
    cue = {c.id: (c.nombre, rub[c.rubro_id]) for c in db.query(Cuenta)}
    fin = {f.id: f.codigo for f in db.query(Financiador)}
    are = {a.id: a.codigo for a in db.query(Area)}
    reg = {r.id: r.codigo for r in db.query(Region)}

    def etiquetas(o):
        cuenta, rubro = cue[o.cuenta_id]
        return {"fondo": fin[o.financiador_id], "rubro": rubro, "cuenta": cuenta, "area": are[o.area_id], "region": reg[o.region_id]}

    filas = [
        {"id": f"m{m.id}", "tipo": "ejec", "mes": m.mes, "descripcion": m.descripcion, "cuenta_contable": m.cuenta_contable,
         "etiquetas": etiquetas(m)}
        for m in db.query(Movimiento)
    ]
    filas += [{"id": f"p{p.id}", "tipo": "ppto", "mes": p.mes, "etiquetas": etiquetas(p)} for p in db.query(Presupuesto)]
    return filas


def entrenar(filas: list[dict]) -> dict[str, NaiveBayes]:
    return {c: NaiveBayes().entrenar([(rasgos(f, c), f["etiquetas"][c]) for f in filas if f["etiquetas"].get(c)]) for c in CAMPOS}


def predecir(modelos: dict[str, NaiveBayes], fila: dict, faltantes: list[str]) -> dict:
    out = {}
    for campo in faltantes:
        res = modelos[campo].predecir(rasgos(fila, campo))
        if res:
            out[campo] = {"valor": res[0][0], "confianza": round(res[0][1], 4),
                          "alternativas": [[v, round(p, 4)] for v, p in res[1:]]}
    return out


def evaluar(filas: list[dict], umbral: float = 0.8) -> dict:
    """Validación hold-out: oculta cada etiqueta en 1 de cada 5 filas y mide aciertos."""
    prueba = [f for i, f in enumerate(filas) if i % 5 == 0]
    modelos = entrenar([f for i, f in enumerate(filas) if i % 5 != 0])
    por_campo = {}
    for campo in CAMPOS:
        n = ok = n_alta = ok_alta = 0
        for f in prueba:
            real = f["etiquetas"].get(campo)
            res = modelos[campo].predecir(rasgos(f, campo))
            if not real or not res:
                continue
            n += 1
            ok += res[0][0] == real
            if res[0][1] >= umbral:
                n_alta += 1
                ok_alta += res[0][0] == real
        por_campo[campo] = {
            "campo": ETIQUETAS_CAMPO[campo], "evaluadas": n,
            "precision": round(ok / n, 4) if n else None,
            "cobertura_alta_confianza": round(n_alta / n, 4) if n else None,
            "precision_alta_confianza": round(ok_alta / n_alta, 4) if n_alta else None,
        }
    total_n = sum(p["evaluadas"] for p in por_campo.values())
    total_ok = sum(round((p["precision"] or 0) * p["evaluadas"]) for p in por_campo.values())
    return {"umbral": umbral, "filas_prueba": len(prueba), "precision_global": round(total_ok / total_n, 4) if total_n else None,
            "campos": por_campo}
