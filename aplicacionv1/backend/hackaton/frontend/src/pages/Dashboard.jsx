import { useEffect, useState } from 'react'
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api, bs, corto, pct, qs } from '../api'
import Filtros from './Filtros'

// Roles de color: ejecutado = serie principal; programado/vigente = referencia neutra
const C = { ejecutado: '#2a78d6', programado: '#b8c4d3', anterior: '#eb6834', grid: '#e6eaf0', eje: '#6b7686' }

const estado = (p) => (p === null || p === undefined ? null : p < 40 ? 'bajo' : p < 75 ? 'medio' : 'alto')
const ICONO = { bajo: '▼', medio: '■', alto: '▲' }
const ICONO_HALLAZGO = { alerta: '!', info: 'i', ok: '✓' }
const etiqueta = (s) => s.split(' - ').slice(1).join(' - ') || s

function Estado({ p }) {
  const e = estado(p)
  if (!e) return <span className="muted">—</span>
  return <span className={`estado ${e}`}><span aria-hidden>{ICONO[e]}</span>{pct(p)}</span>
}

function Kpi({ titulo, valor, detalle, avance, tono }) {
  return (
    <div className={`kpi ${tono || ''}`}>
      <span>{titulo}</span>
      <strong>{valor}</strong>
      {avance !== undefined && (
        <div className="kpi-barra" title={pct(avance)}><div style={{ width: `${Math.min(avance || 0, 100)}%` }} /></div>
      )}
      {detalle && <small>{detalle}</small>}
    </div>
  )
}

// Barras tipo "bullet": la pista es el presupuesto vigente y el relleno lo ejecutado.
// Clic en una fila = filtrar todo el tablero por ese elemento.
function Bullets({ filas, dim, filtros, onFiltrar }) {
  const max = Math.max(...filas.map((f) => f.vigente), 1)
  const activos = filtros[dim] || []
  return (
    <div className="bullets">
      {filas.map((f) => {
        const activo = activos.includes(f.id)
        return (
          <button key={f.id} className={`bullet ${activo ? 'activo' : ''}`} onClick={() => onFiltrar(dim, f.id)}
            title={`${f.nombre}\nVigente: Bs ${bs(f.vigente)}\nEjecutado: Bs ${bs(f.ejecutado)}\nSaldo: Bs ${bs(f.saldo)}\nClic para filtrar`}>
            <span className="bullet-nombre">{etiqueta(f.nombre)}</span>
            <span className="bullet-carril">
              <span className="bullet-pista" style={{ width: `${(f.vigente / max) * 100}%` }}>
                <span className="bullet-relleno" style={{ width: `${f.vigente ? Math.min((f.ejecutado / f.vigente) * 100, 100) : 0}%` }} />
              </span>
            </span>
            <span className="bullet-valor"><Estado p={f.porcentaje} /><small>Bs {corto(f.ejecutado)} / {corto(f.vigente)}</small></span>
          </button>
        )
      })}
    </div>
  )
}

function TooltipBs({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="tooltip">
      <strong>{label}</strong>
      {payload.filter((p) => p.value !== null && p.value !== undefined).map((p) => (
        <div key={p.dataKey}><i style={{ background: p.color }} />{p.name}<b>Bs {bs(p.value)}</b></div>
      ))}
    </div>
  )
}

export default function Dashboard({ gestion, catalogos, puedeValidar, presentacion, onPresentacion, irA }) {
  const [filtros, setFiltros] = useState({})
  const [d, setD] = useState(null)

  useEffect(() => {
    let vigente = true
    api(`/dashboard?${qs({ gestion, ...filtros })}`).then((r) => vigente && setD(r))
    return () => { vigente = false }
  }, [gestion, filtros])

  const filtrar = (dim, id) => {
    const actual = filtros[dim] || []
    setFiltros({ ...filtros, [dim]: actual.includes(id) ? actual.filter((x) => x !== id) : [...actual, id] })
  }

  if (!d) return <div className="muted">Cargando…</div>
  const t = d.total
  const cumplimiento = d.programado_a_la_fecha ? (t.ejecutado / d.programado_a_la_fecha) * 100 : null
  const ultimoMes = [...d.mensual].reverse().find((m) => m.ejecutado)
  const mensual = d.mensual.map((m, i) => ({ ...m, anterior: d.mensual_anterior ? d.mensual_anterior[i].acumulado : null }))
  const fecha = d.ultima_actualizacion
    ? new Date(`${d.ultima_actualizacion}T00:00`).toLocaleDateString('es-BO', { day: 'numeric', month: 'long', year: 'numeric' })
    : null
  const eje = { stroke: C.grid, tick: { fill: C.eje, fontSize: 12 } }

  return (
    <div className="page dashboard">
      <div className="hero">
        <div>
          <span className="hero-eyebrow">Ejecución presupuestaria · Gestión {gestion}</span>
          <h2>{pct(t.porcentaje)} del presupuesto ejecutado</h2>
          <p className="muted">
            {fecha ? `Datos al ${fecha}` : 'Sin movimientos registrados'} · Expresado en bolivianos
            {d.pendientes > 0 && puedeValidar && (
              <> · <button className="link" onClick={() => irA('validacion')}>{d.pendientes} filas por validar</button></>
            )}
          </p>
        </div>
        <button onClick={onPresentacion}>{presentacion ? 'Salir de presentación' : '⛶ Modo presentación'}</button>
      </div>

      <Filtros catalogos={catalogos} valor={filtros} onChange={setFiltros} />

      <div className="kpis kpis-5">
        <Kpi titulo="Presupuesto vigente" valor={`Bs ${corto(t.vigente)}`} detalle={`Bs ${bs(t.vigente)}`} />
        <Kpi titulo="Ejecutado" valor={`Bs ${corto(t.ejecutado)}`} avance={t.porcentaje} tono={estado(t.porcentaje)}
          detalle={`${pct(t.porcentaje)} del vigente`} />
        <Kpi titulo="Saldo por ejecutar" valor={`Bs ${corto(t.saldo)}`} detalle={`Bs ${bs(t.saldo)}`} />
        <Kpi titulo={`Cumplimiento a ${ultimoMes?.nombre || 'la fecha'}`} valor={pct(cumplimiento)} avance={cumplimiento}
          tono={estado(cumplimiento)} detalle={`Ejecutado vs programado (Bs ${corto(d.programado_a_la_fecha)})`} />
        <Kpi titulo="Sin programar (PTTO)" valor={`Bs ${corto(d.sin_programar)}`}
          detalle={`${pct(t.vigente ? (d.sin_programar / t.vigente) * 100 : null)} del presupuesto`} />
      </div>

      {d.hallazgos.length > 0 && (
        <section className="card hallazgos">
          <h3>Hallazgos clave</h3>
          <ul>
            {d.hallazgos.map((h, i) => (
              <li key={i} className={h.tipo}>
                <span className="hallazgo-icono" aria-label={h.tipo}>{ICONO_HALLAZGO[h.tipo]}</span>{h.texto}
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="grid2">
        <section className="card">
          <h3>Programado vs ejecutado por mes</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={d.mensual} barGap={2} barCategoryGap="22%">
              <CartesianGrid stroke={C.grid} vertical={false} />
              <XAxis dataKey="nombre" {...eje} />
              <YAxis tickFormatter={corto} {...eje} width={48} />
              <Tooltip content={<TooltipBs />} cursor={{ fill: 'rgba(31,58,95,.05)' }} />
              <Legend iconType="circle" />
              <Bar dataKey="presupuesto" name="Programado" fill={C.programado} radius={[4, 4, 0, 0]} />
              <Bar dataKey="ejecutado" name="Ejecutado" fill={C.ejecutado} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </section>
        <section className="card">
          <h3>Ejecución acumulada</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={mensual}>
              <CartesianGrid stroke={C.grid} vertical={false} />
              <XAxis dataKey="nombre" {...eje} />
              <YAxis tickFormatter={corto} {...eje} width={48} />
              <Tooltip content={<TooltipBs />} />
              <Legend iconType="circle" />
              <Line type="monotone" dataKey="presupuesto_acumulado" name="Programado acumulado" stroke={C.programado}
                strokeWidth={2} strokeDasharray="6 4" dot={false} />
              <Line type="monotone" dataKey="acumulado" name={`Ejecutado ${gestion}`} stroke={C.ejecutado} strokeWidth={2}
                dot={{ r: 4 }} activeDot={{ r: 6 }} />
              {d.mensual_anterior && (
                <Line type="monotone" dataKey="anterior" name={`Ejecutado ${d.gestion_anterior}`} stroke={C.anterior} strokeWidth={2} dot={false} />
              )}
            </LineChart>
          </ResponsiveContainer>
        </section>

        <section className="card">
          <h3>Por financiador <small>clic para filtrar</small></h3>
          <Bullets filas={d.por_financiador} dim="financiador" filtros={filtros} onFiltrar={filtrar} />
          <h3 className="sub">Por región</h3>
          <Bullets filas={d.por_region} dim="region" filtros={filtros} onFiltrar={filtrar} />
        </section>
        <section className="card">
          <h3>Por rubro <small>clic para filtrar</small></h3>
          <Bullets filas={d.por_rubro} dim="rubro" filtros={filtros} onFiltrar={filtrar} />
        </section>
        <section className="card">
          <h3>Por área</h3>
          <Bullets filas={d.por_area} dim="area" filtros={filtros} onFiltrar={filtrar} />
        </section>
        <section className="card">
          <h3>Cuentas con mayor saldo por ejecutar</h3>
          <table className="compacta">
            <thead><tr><th>Cuenta</th><th>Vigente</th><th>Saldo</th><th>% Ejec.</th></tr></thead>
            <tbody>
              {d.top_saldos.map((c, i) => (
                <tr key={i}>
                  <td className="txt">{c.cuenta}<small className="muted block">{c.rubro}</small></td>
                  <td>{corto(c.vigente)}</td><td><b>{corto(c.saldo)}</b></td><td><Estado p={c.porcentaje} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
      <p className="muted small leyenda">
        Estado de ejecución: <span className="estado bajo">▼ menos de 40%</span> <span className="estado medio">■ 40–75%</span>{' '}
        <span className="estado alto">▲ 75% o más</span> · El presupuesto “programado” es el asignado a cada mes; “PTTO” es el aún no asignado.
      </p>
    </div>
  )
}
