import { useEffect, useRef, useState } from 'react'
import { api, bs, descargar } from '../api'

const ICONO_HOJA = { base: '✓', plantilla: '✓', pivot: '▦', auxiliar: '⚙', otra: '·' }
const MESES = ['PTTO', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
const letra = (i) => (i < 26 ? String.fromCharCode(65 + i) : String.fromCharCode(64 + Math.floor(i / 26)) + String.fromCharCode(65 + (i % 26)))
const celda = (v) => (v === null || v === undefined ? '' : typeof v === 'number' ? v.toLocaleString('es-BO', { maximumFractionDigits: 2 }) : String(v))

// Vista de una hoja como cuadrícula tipo Excel
function Hoja({ hoja }) {
  const [soloIncompletas, setSoloIncompletas] = useState(false)
  const grilla = useRef(null)
  // Al filtrar incompletas, lleva la vista hasta la primera celda faltante
  useEffect(() => {
    if (soloIncompletas) grilla.current?.querySelector('td.falta')?.scrollIntoView({ inline: 'center', block: 'nearest' })
  }, [soloIncompletas])
  const filas = soloIncompletas ? hoja.incompletas || [] : hoja.muestra
  const nIncompletas = hoja.incompletas?.length || 0
  return (
    <div className="hoja">
      <div className="hoja-barra">
        <span className={`hoja-tipo ${hoja.tipo}`}>{hoja.tipo_texto}</span>
        <span className="muted small">
          {hoja.total_filas.toLocaleString('es-BO')} filas · {hoja.columnas.length} columnas · encabezado en la fila {hoja.fila_encabezado}
          {!soloIncompletas && hoja.total_filas > hoja.muestra.length && ` · mostrando las primeras ${hoja.muestra.length}`}
        </span>
        {nIncompletas > 0 && (
          <label className="inline small">
            <input type="checkbox" checked={soloIncompletas} onChange={(e) => setSoloIncompletas(e.target.checked)} />
            Solo filas incompletas ({nIncompletas})
          </label>
        )}
      </div>
      {hoja.tipo === 'pivot' && <p className="muted small nota-hoja">Tabla dinámica del archivo original: no se importa, el sistema la reproduce como reporte.</p>}
      {hoja.tipo === 'otra' && <p className="muted small nota-hoja">Hoja no reconocida: se ignora al importar.</p>}
      {hoja.columnas.length === 0 ? (
        <div className="muted vacio">Hoja vacía</div>
      ) : (
        <div className="grilla-wrap" ref={grilla}>
          <table className="grilla">
            <thead>
              <tr><th className="esquina" />{hoja.columnas.map((_, i) => <th key={i} className="letra">{letra(i)}</th>)}</tr>
              <tr>
                <th className="num">{hoja.fila_encabezado}</th>
                {hoja.columnas.map((c, i) => (
                  <th key={i} className={c.significado ? 'mapeada' : ''} title={c.significado ? `Se importa como: ${c.significado}` : ''}>
                    {c.nombre}
                    {c.significado && <small>→ {c.significado}</small>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filas.map((f) => {
                const falt = new Set(f.faltantes || [])
                return (
                  <tr key={f.fila} className={falt.size ? 'incompleta' : ''}>
                    <td className="num">{f.fila}</td>
                    {hoja.columnas.map((_, i) => (
                      <td key={i} className={falt.has(i) ? 'falta' : typeof f.valores[i] === 'number' ? 'n' : ''}
                        title={falt.has(i) ? 'Etiqueta faltante: se predecirá y quedará para validar' : undefined}>
                        {falt.has(i) ? '— falta —' : celda(f.valores[i])}
                      </td>
                    ))}
                  </tr>
                )
              })}
              {!filas.length && <tr><td colSpan={hoja.columnas.length + 1} className="muted vacio">Sin filas</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function Analisis({ a }) {
  return (
    <div className="analisis">
      <div className="kpis">
        <div className="kpi"><span>Gestión detectada</span><strong>{a.gestion ?? '—'}</strong><small>{a.filas.toLocaleString('es-BO')} filas en la base</small></div>
        <div className="kpi"><span>Presupuesto</span><strong>Bs {bs(a.total_presupuesto)}</strong><small>{a.financiadores.length} financiadores · {a.regiones.join(', ')}</small></div>
        <div className="kpi"><span>Ejecución</span><strong>Bs {bs(a.total_ejecucion)}</strong><small>{a.movimientos.toLocaleString('es-BO')} movimientos listos</small></div>
        <div className={`kpi ${a.filas_incompletas ? 'medio' : 'alto'}`}>
          <span>Filas incompletas</span><strong>{a.filas_incompletas}</strong>
          <small>{a.filas_incompletas ? 'irán a Validación de datos' : 'todas las filas están completas'}</small>
        </div>
      </div>
      <div className="analisis-detalle">
        {a.faltantes_por_campo.length > 0 && (
          <div>
            <b>Etiquetas faltantes:</b>{' '}
            {a.faltantes_por_campo.map((c) => <span key={c.campo} className="chip-dato">{c.campo}: {c.filas}</span>)}
            <span className="muted small"> · Bs {bs(a.presupuesto_pendiente)} ppto. y Bs {bs(a.ejecucion_pendiente)} ejec. quedarán pendientes</span>
          </div>
        )}
        <div>
          <b>Filas por mes:</b>{' '}
          {a.filas_por_mes.map((m) => <span key={m.mes} className="chip-dato">{MESES[m.mes]}: {m.filas}</span>)}
        </div>
        {a.filas_con_error > 0 && (
          <div className="error small">
            {a.filas_con_error} filas con error se omitirán: {a.errores.slice(0, 5).map((e) => `fila ${e.fila} (${e.error})`).join('; ')}
          </div>
        )}
        {a.reemplaza && (
          <div className="aviso small">
            ⚠ La gestión {a.gestion} ya tiene datos cargados ({a.reemplaza.movimientos.toLocaleString('es-BO')} movimientos,{' '}
            {a.reemplaza.lineas_presupuesto} líneas de presupuesto{a.reemplaza.pendientes ? `, ${a.reemplaza.pendientes} filas pendientes` : ''}).
            Al importar <b>se reemplazarán</b> por este archivo. Las demás gestiones no se tocan.
          </div>
        )}
      </div>
    </div>
  )
}

export default function Importar({ onImportado, irA }) {
  const [archivo, setArchivo] = useState(null)
  const [gestion, setGestion] = useState('')
  const [vista, setVista] = useState(null)
  const [hojaActiva, setHojaActiva] = useState(null)
  const [resultado, setResultado] = useState(null)
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState('')
  const [historial, setHistorial] = useState([])
  const [arrastrando, setArrastrando] = useState(false)

  const cargarHistorial = () => api('/importaciones').then(setHistorial)
  useEffect(() => { cargarHistorial() }, [])

  const formulario = (f) => {
    const fd = new FormData()
    fd.append('archivo', f)
    if (gestion) fd.append('gestion', gestion)
    return fd
  }

  const elegir = async (f) => {
    if (!f) return
    setArchivo(f); setVista(null); setResultado(null); setError('')
    if (!f.name.toLowerCase().endsWith('.xlsx')) return setError('Solo se aceptan archivos Excel .xlsx')
    setCargando('Leyendo el archivo…')
    try {
      const v = await api('/importar/previsualizar', { method: 'POST', body: formulario(f) })
      setVista(v)
      setHojaActiva(v.hoja_importable ?? v.hojas[0]?.nombre)
    } catch (e) {
      setError(e.message)
    } finally {
      setCargando('')
    }
  }

  const plantilla = vista?.hojas.find((h) => h.tipo === 'plantilla')
  const importable = vista && (vista.hoja_importable || plantilla)

  const importar = async () => {
    setCargando('Importando…'); setError('')
    const fd = formulario(archivo)
    fd.append('tipo', plantilla?.tipo_texto.includes('presupuesto') && !vista.hoja_importable ? 'presupuestos' : 'movimientos')
    try {
      setResultado(await api('/importar', { method: 'POST', body: fd }))
      setVista(null)
      cargarHistorial()
      onImportado()
    } catch (e) {
      setError(e.message)
    } finally {
      setCargando('')
    }
  }

  const hoja = vista?.hojas.find((h) => h.nombre === hojaActiva)

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h2>Cargar datos del sistema contable</h2>
          <p className="muted">Revisa el archivo antes de importarlo: cada hoja del Excel aparece como una pestaña del cuaderno.</p>
        </div>
        <div className="acciones">
          <button className="link" onClick={() => descargar('/plantilla/movimientos', 'plantilla_movimientos.xlsx')}>Plantilla de movimientos</button>
          <button className="link" onClick={() => descargar('/plantilla/presupuestos', 'plantilla_presupuestos.xlsx')}>Plantilla de presupuesto</button>
        </div>
      </div>

      <label
        className={`zona-archivo ${arrastrando ? 'arrastrando' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setArrastrando(true) }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={(e) => { e.preventDefault(); setArrastrando(false); elegir(e.dataTransfer.files[0]) }}
      >
        <input type="file" accept=".xlsx" onChange={(e) => { elegir(e.target.files[0]); e.target.value = '' }} />
        <strong>{archivo ? `📒 ${archivo.name}` : 'Arrastra aquí el Excel o haz clic para elegirlo'}</strong>
        <span className="muted small">
          {archivo ? `${(archivo.size / 1024).toFixed(0)} KB · clic para elegir otro archivo` : 'Formato .xlsx exportado del sistema contable (hoja BD)'}
        </span>
      </label>

      {cargando && <div className="muted">{cargando}</div>}
      {error && <div className="error">{error}</div>}

      {vista && (
        <section className="card cuaderno">
          <div className="cuaderno-cabecera">
            <div>
              <h3>Vista previa · {vista.archivo}</h3>
              <p className="muted small">
                {vista.hojas.length} hojas.{' '}
                {vista.hoja_importable ? <>Se importará la hoja <b>{vista.hoja_importable}</b>; las demás se muestran como referencia.</> : vista.mensaje}
              </p>
            </div>
            <div className="acciones">
              <label className="inline small">Gestión
                <input type="number" placeholder={vista.analisis?.gestion ?? 'auto'} value={gestion} onChange={(e) => setGestion(e.target.value)} style={{ width: 90 }} />
              </label>
              {gestion && <button className="link" onClick={() => elegir(archivo)}>Recalcular</button>}
              <button className="link" onClick={() => { setVista(null); setArchivo(null) }}>Cancelar</button>
              <button className="primary" disabled={!importable || !!cargando} onClick={importar}>
                {vista.analisis?.reemplaza ? 'Reemplazar e importar' : 'Importar'}
              </button>
            </div>
          </div>

          {vista.analisis && <Analisis a={vista.analisis} />}

          <div className="pestanas" role="tablist">
            {vista.hojas.map((h) => (
              <button key={h.nombre} role="tab" aria-selected={h.nombre === hojaActiva}
                className={`pestana ${h.tipo} ${h.nombre === hojaActiva ? 'activa' : ''}`} onClick={() => setHojaActiva(h.nombre)}
                title={h.tipo_texto}>
                <span className="pestana-icono">{ICONO_HOJA[h.tipo]}</span>{h.nombre}
                {h.incompletas?.length > 0 && <span className="pestana-alerta">{h.incompletas.length}</span>}
              </button>
            ))}
          </div>
          {hoja && <Hoja key={hoja.nombre} hoja={hoja} />}
        </section>
      )}

      {resultado && (
        <section className="card">
          <div className={resultado.filas_error ? 'aviso' : 'ok'}>
            <strong>✓ {resultado.filas_ok} filas importadas · {resultado.filas_error} con error</strong>
            {resultado.resumen && (
              <div className="small">
                Gestión {resultado.resumen.gestion} · {resultado.resumen.movimientos} movimientos ·
                Presupuesto Bs {bs(resultado.resumen.total_presupuesto)} · Ejecución Bs {bs(resultado.resumen.total_ejecucion)}
              </div>
            )}
            {resultado.errores?.slice(0, 10).map((e) => <div key={e.fila} className="small">Fila {e.fila}: {e.error}</div>)}
          </div>
          {resultado.resumen?.pendientes > 0 && (
            <div className="aviso">
              <strong>{resultado.resumen.pendientes} filas con etiquetas faltantes</strong> quedaron en revisión con etiquetas predichas.{' '}
              <button type="button" className="link" onClick={() => irA('validacion')}>Ir a validarlas →</button>
            </div>
          )}
          {resultado.resumen?.advertencias?.length > 0 && (
            <div className="aviso small">
              <strong>Calidad de datos ({resultado.resumen.advertencias.length} advertencias)</strong>
              <ul>{resultado.resumen.advertencias.map((a, i) => <li key={i}>{a}</li>)}</ul>
            </div>
          )}
        </section>
      )}

      <section className="card">
        <h3>Historial de importaciones</h3>
        <table>
          <thead><tr><th>Fecha</th><th>Archivo</th><th>Tipo</th><th>Gestión</th><th>Filas OK</th><th>Pendientes</th><th>Errores</th></tr></thead>
          <tbody>
            {historial.map((i) => (
              <tr key={i.id}>
                <td>{i.fecha.slice(0, 16).replace('T', ' ')}</td><td className="txt">{i.archivo}</td><td>{i.tipo}</td>
                <td>{i.resumen?.gestion ?? '—'}</td><td>{i.filas_ok}</td><td>{i.resumen?.pendientes ?? 0}</td><td>{i.filas_error}</td>
              </tr>
            ))}
            {!historial.length && <tr><td colSpan={7} className="muted">Sin importaciones aún</td></tr>}
          </tbody>
        </table>
      </section>
    </div>
  )
}
