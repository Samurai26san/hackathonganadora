import { useEffect, useMemo, useState } from 'react'
import { api, bs, pct } from '../api'

const CAMPOS = [
  ['fondo', 'Financiador'],
  ['rubro', 'Rubro'],
  ['cuenta', 'Cuenta'],
  ['area', 'Área'],
  ['region', 'Región'],
]
const nivel = (c) => (c >= 0.8 ? 'alto' : c >= 0.5 ? 'medio' : 'bajo')

function CeldaEtiqueta({ fila, campo, edicion, onEditar, opciones, soloLectura }) {
  const original = fila.etiquetas[campo]
  if (original) return <td className="txt etiqueta-original">{original}</td>
  if (soloLectura) {
    return (
      <td className="txt">
        <span className="etiqueta-completada">{fila.valores?.[campo]}</span>
        <span className={`badge ${fila.origen === 'manual' ? 'manual' : 'alto'}`}>completada</span>
      </td>
    )
  }
  const pred = fila.prediccion[campo]
  const editado = edicion !== undefined
  const valor = editado ? edicion : pred?.valor ?? ''
  const alternativas = pred?.alternativas?.map(([v, p]) => `${v} (${Math.round(p * 100)}%)`).join('\n')
  return (
    <td className={`txt faltante ${!valor ? 'vacia' : ''}`}>
      <input list={`op-${campo}`} value={valor} placeholder="Completar…" onChange={(e) => onEditar(campo, e.target.value)} />
      {editado ? (
        <span className="badge manual">✎ manual</span>
      ) : pred ? (
        <span className={`badge ${nivel(pred.confianza)}`} title={alternativas ? `Otras opciones:\n${alternativas}` : ''}>
          IA {Math.round(pred.confianza * 100)}%
        </span>
      ) : (
        <span className="badge bajo">sin predicción</span>
      )}
    </td>
  )
}

function Evaluacion({ ev }) {
  if (!ev) return null
  return (
    <details className="card evaluacion">
      <summary>
        <strong>¿Qué tan confiable es la predicción?</strong>{' '}
        <span className="muted">Precisión global {pct(ev.precision_global * 100)} medida ocultando etiquetas de {ev.filas_prueba} filas conocidas</span>
      </summary>
      <table className="compacta">
        <thead><tr><th>Campo</th><th>Precisión</th><th>Filas con confianza ≥ {Math.round(ev.umbral * 100)}%</th><th>Precisión en esas filas</th></tr></thead>
        <tbody>
          {Object.values(ev.campos).map((c) => (
            <tr key={c.campo}>
              <td>{c.campo}</td><td>{pct(c.precision * 100)}</td>
              <td>{pct(c.cobertura_alta_confianza * 100)}</td><td><b>{pct(c.precision_alta_confianza * 100)}</b></td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="muted small">
        El modelo (Naive Bayes) aprende de las filas completas: código y nombre de la cuenta contable, palabras de la glosa,
        prefijo de la regional y las demás etiquetas de la fila. Cada fila validada se suma al entrenamiento.
      </p>
    </details>
  )
}

export default function Validacion({ gestion, onValidado }) {
  const [estado, setEstado] = useState('pendiente')
  const [datos, setDatos] = useState(null)
  const [opciones, setOpciones] = useState({})
  const [ev, setEv] = useState(null)
  const [ediciones, setEdiciones] = useState({}) // {id: {campo: valor}}
  const [seleccion, setSeleccion] = useState(new Set())
  const [campoFiltro, setCampoFiltro] = useState('')
  const [umbral, setUmbral] = useState(80)
  const [mensaje, setMensaje] = useState(null)
  const [ocupado, setOcupado] = useState(false)

  const cargar = () => {
    api(`/pendientes?gestion=${gestion}&estado=${estado}`).then(setDatos)
    setSeleccion(new Set())
  }
  useEffect(cargar, [gestion, estado])
  useEffect(() => {
    api('/pendientes/opciones').then(setOpciones)
    api('/prediccion/evaluacion').then(setEv)
  }, [])

  const filas = useMemo(
    () => (datos?.filas || []).filter((f) => !campoFiltro || f.faltantes.includes(campoFiltro)),
    [datos, campoFiltro],
  )
  const altaConfianza = (datos?.filas || []).filter((f) => f.confianza_min !== null && f.confianza_min * 100 >= umbral)
  const soloLectura = estado !== 'pendiente'

  const editar = (id, campo, valor) => setEdiciones((e) => ({ ...e, [id]: { ...(e[id] || {}), [campo]: valor } }))
  const alternar = (id) => setSeleccion((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })
  const todas = () => setSeleccion(seleccion.size === filas.length ? new Set() : new Set(filas.map((f) => f.id)))

  const ejecutar = async (accion, cuerpo, texto) => {
    setOcupado(true)
    setMensaje(null)
    try {
      const r = await api(`/pendientes/${accion}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cuerpo),
      })
      let t = texto(r)
      if (r.incompletas?.length) t += ` · ${r.incompletas.length} sin validar porque aún les faltan etiquetas (filas ${r.incompletas.slice(0, 8).join(', ')})`
      setMensaje({ tipo: r.incompletas?.length ? 'aviso' : 'ok', texto: t })
      cargar()
      onValidado?.()
      if (accion !== 'descartar') api('/prediccion/evaluacion').then(setEv)
    } catch (e) {
      setMensaje({ tipo: 'error', texto: e.message })
    } finally {
      setOcupado(false)
    }
  }
  const validar = (ids) => ejecutar('validar', { ids, valores: Object.fromEntries(ids.filter((i) => ediciones[i]).map((i) => [i, ediciones[i]])) },
    (r) => `${r.validadas} filas validadas e incorporadas a los reportes`)
  const validarUmbral = () => ejecutar('validar', { umbral: umbral / 100, gestion },
    (r) => `${r.validadas} filas con confianza ≥ ${umbral}% validadas en bloque`)
  const descartar = (ids) => ejecutar('descartar', { ids }, (r) => `${r.descartadas} filas descartadas`)
  const repredecir = () => ejecutar('predecir', {}, (r) => `Modelo reentrenado: ${r.filas} filas con nuevas predicciones`)

  if (!datos) return <div className="muted">Cargando…</div>
  const c = datos.conteo
  const sel = [...seleccion]

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Validación de datos · {gestion}</h2>
          <p className="muted">Filas importadas con etiquetas faltantes. No suman en los reportes hasta que se validen.</p>
        </div>
        <button onClick={repredecir} disabled={ocupado || !c.pendiente}>↻ Volver a predecir</button>
      </div>

      <div className="kpis">
        <div className="kpi medio"><span>Por validar</span><strong>{c.pendiente}</strong>
          <small>Bs {bs((datos.filas || []).reduce((s, f) => s + f.presupuesto, 0))} ppto. en esta vista</small></div>
        <div className="kpi alto"><span>Predicción con confianza ≥ {umbral}%</span><strong>{estado === 'pendiente' ? altaConfianza.length : '—'}</strong>
          <small>listas para validar en bloque</small></div>
        <div className="kpi"><span>Validadas</span><strong>{c.validada}</strong><small>{c.descartada} descartadas</small></div>
        <div className="kpi"><span>Precisión del modelo</span><strong>{ev ? pct(ev.precision_global * 100) : '…'}</strong>
          <small>evaluada con datos conocidos</small></div>
      </div>

      <Evaluacion ev={ev} />

      <div className="tabs">
        {[['pendiente', 'Por validar'], ['validada', 'Validadas'], ['descartada', 'Descartadas']].map(([k, l]) => (
          <button key={k} className={estado === k ? 'active' : ''} onClick={() => { setEstado(k); setMensaje(null) }}>{l} ({c[k]})</button>
        ))}
      </div>

      <div className="barra-validacion">
        <label className="inline">Falta
          <select value={campoFiltro} onChange={(e) => setCampoFiltro(e.target.value)}>
            <option value="">cualquier campo</option>
            {CAMPOS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
        </label>
        {!soloLectura && (
          <>
            <label className="inline">Confianza mínima
              <input type="range" min={50} max={99} value={umbral} onChange={(e) => setUmbral(Number(e.target.value))} />
              <b>{umbral}%</b>
            </label>
            <button className="primary" disabled={ocupado || !altaConfianza.length} onClick={validarUmbral}>
              ✓ Validar {altaConfianza.length} con confianza ≥ {umbral}%
            </button>
            <button disabled={ocupado || !sel.length} onClick={() => validar(sel)}>✓ Validar seleccionadas ({sel.length})</button>
            <button disabled={ocupado || !sel.length} onClick={() => descartar(sel)}>✕ Descartar seleccionadas</button>
          </>
        )}
      </div>

      {mensaje && <div className={mensaje.tipo}>{mensaje.texto}</div>}

      <div className="tabla-wrap">
        <table className="validacion">
          <thead>
            <tr>
              {!soloLectura && <th><input type="checkbox" checked={filas.length > 0 && seleccion.size === filas.length} onChange={todas} /></th>}
              <th>Fila</th><th>Mes</th><th>Detalle</th><th>Presupuesto</th><th>Ejecución</th>
              {CAMPOS.map(([k, l]) => <th key={k}>{l}</th>)}
              <th>{soloLectura ? 'Validó' : 'Acciones'}</th>
            </tr>
          </thead>
          <tbody>
            {filas.map((f) => (
              <tr key={f.id} className={seleccion.has(f.id) ? 'seleccionada' : ''}>
                {!soloLectura && <td><input type="checkbox" checked={seleccion.has(f.id)} onChange={() => alternar(f.id)} /></td>}
                <td>{f.fila}</td>
                <td>{f.mes_nombre}</td>
                <td className="txt detalle">
                  {f.comprobante && <b>{f.comprobante} </b>}{f.descripcion}
                  {f.cuenta_contable && <small className="muted block">{f.cuenta_contable}</small>}
                </td>
                <td>{bs(f.presupuesto)}</td>
                <td>{bs(f.ejecucion)}</td>
                {CAMPOS.map(([k]) => (
                  <CeldaEtiqueta key={k} fila={f} campo={k} edicion={ediciones[f.id]?.[k]} soloLectura={soloLectura}
                    onEditar={(campo, v) => editar(f.id, campo, v)} opciones={opciones[k]} />
                ))}
                <td className="acciones-fila">
                  {soloLectura ? (
                    <small>{f.validado_por}<br />{f.origen}</small>
                  ) : (
                    <>
                      <button title="Validar esta fila" disabled={ocupado} onClick={() => validar([f.id])}>✓</button>
                      <button title="Descartar esta fila" disabled={ocupado} onClick={() => descartar([f.id])}>✕</button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {!filas.length && (
              <tr><td colSpan={13} className="muted vacio">
                {estado === 'pendiente' ? 'No hay filas pendientes de validación 🎉' : 'Sin filas en esta vista'}
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
      {CAMPOS.map(([k]) => (
        <datalist key={k} id={`op-${k}`}>{(opciones[k] || []).map((v) => <option key={v} value={v} />)}</datalist>
      ))}
    </div>
  )
}
