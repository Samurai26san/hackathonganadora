import { useEffect, useState } from 'react'
import { api, bs, descargar, pct, qs } from '../api'
import Filtros from './Filtros'

function Fila({ n, prof, comparar, abiertos, toggle, ruta }) {
  const clave = `${ruta}/${n.nivel}:${n.id}`
  const tieneHijos = n.hijos.length > 0
  const abierto = abiertos.has(clave)
  const c = n.comparativo
  return (
    <>
      <tr className={`nivel-${prof}`}>
        <td style={{ paddingLeft: 12 + prof * 22 }}>
          {tieneHijos ? (
            <button className="expand" onClick={() => toggle(clave)}>{abierto ? '▾' : '▸'}</button>
          ) : <span className="expand-sp" />}
          {n.nombre}
        </td>
        <td>{bs(n.inicial)}</td>
        <td>{bs(n.modificaciones)}</td>
        <td>{bs(n.vigente)}</td>
        <td>{bs(n.ejecutado)}</td>
        <td>{bs(n.saldo)}</td>
        <td><span className={`badge ${n.porcentaje === null ? '' : n.porcentaje < 40 ? 'bajo' : n.porcentaje < 75 ? 'medio' : 'alto'}`}>{pct(n.porcentaje)}</span></td>
        {comparar && <><td>{bs(c.ejecutado)}</td><td className={c.variacion < 0 ? 'neg' : 'pos'}>{bs(c.variacion)}</td><td>{pct(c.variacion_pct)}</td></>}
      </tr>
      {abierto && n.hijos.map((h) => (
        <Fila key={`${h.nivel}:${h.id}`} n={h} prof={prof + 1} comparar={comparar} abiertos={abiertos} toggle={toggle} ruta={clave} />
      ))}
    </>
  )
}

function TablaEjecucion({ rep, comparar }) {
  const [abiertos, setAbiertos] = useState(new Set())
  const toggle = (k) => setAbiertos((s) => { const n = new Set(s); n.has(k) ? n.delete(k) : n.add(k); return n })
  const todas = () => {
    const s = new Set()
    const rec = (nodos, ruta) => nodos.forEach((n) => { const k = `${ruta}/${n.nivel}:${n.id}`; if (n.hijos.length) { s.add(k); rec(n.hijos, k) } })
    rec(rep.filas, '')
    setAbiertos(s)
  }
  const t = rep.total
  return (
    <>
      <div className="tabla-acciones">
        <span className="muted">Niveles: {rep.niveles.map((n) => n.label).join(' → ')}</span>
        <button className="link" onClick={todas}>Expandir todo</button>
        <button className="link" onClick={() => setAbiertos(new Set())}>Contraer todo</button>
      </div>
      <div className="tabla-wrap">
        <table>
          <thead>
            <tr>
              <th>{rep.niveles.map((n) => n.label).join(' / ')}</th>
              <th>Ppto. inicial</th><th>Modificaciones</th><th>Ppto. vigente</th><th>Ejecutado</th><th>Saldo</th><th>% Ejec.</th>
              {comparar && <><th>Ejec. {comparar}</th><th>Variación</th><th>Var. %</th></>}
            </tr>
          </thead>
          <tbody>
            {rep.filas.map((n) => (
              <Fila key={`${n.nivel}:${n.id}`} n={n} prof={0} comparar={comparar} abiertos={abiertos} toggle={toggle} ruta="" />
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td>TOTAL</td><td>{bs(t.inicial)}</td><td>{bs(t.modificaciones)}</td><td>{bs(t.vigente)}</td>
              <td>{bs(t.ejecutado)}</td><td>{bs(t.saldo)}</td><td>{pct(t.porcentaje)}</td>
              {comparar && <><td>{bs(t.comparativo.ejecutado)}</td><td>{bs(t.comparativo.variacion)}</td><td>{pct(t.comparativo.variacion_pct)}</td></>}
            </tr>
          </tfoot>
        </table>
      </div>
    </>
  )
}

const POR_PAGINA = 100

function TablaMovimientos({ rep, pagina, setPagina }) {
  const paginas = Math.ceil(rep.total_registros / POR_PAGINA)
  return (
    <>
      <div className="tabla-acciones">
        <span className="muted">{rep.total_registros} movimientos · Total Bs {bs(rep.total_monto)}</span>
        {paginas > 1 && (
          <span className="paginador">
            <button disabled={pagina === 0} onClick={() => setPagina(pagina - 1)}>‹</button>
            {pagina + 1} / {paginas}
            <button disabled={pagina >= paginas - 1} onClick={() => setPagina(pagina + 1)}>›</button>
          </span>
        )}
      </div>
      <div className="tabla-wrap">
        <table>
          <thead>
            <tr><th>Fecha</th><th>Comprobante</th><th>Descripción</th><th>Cuenta contable</th><th>Rubro / Cuenta</th><th>Financiador</th><th>Área</th><th>Región</th><th>T/C</th><th>Ejecución Bs</th><th>Ejecución USD</th></tr>
          </thead>
          <tbody>
            {rep.filas.map((m) => (
              <tr key={m.id}>
                <td>{m.fecha}</td><td>{m.comprobante}</td><td className="txt">{m.descripcion}</td>
                <td className="txt">{m.cuenta_contable}</td><td className="txt">{m.rubro} / {m.cuenta}</td><td className="txt">{m.financiador}</td>
                <td className="txt">{m.area}</td><td className="txt">{m.region}</td><td>{m.tipo_cambio}</td>
                <td>{bs(m.monto_bs)}</td><td>{bs(m.monto_usd)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

export default function Reportes({ gestion, catalogos }) {
  const [reporte, setReporte] = useState('rubro-cuenta')
  const [filtros, setFiltros] = useState({})
  const [comparar, setComparar] = useState('')
  const [pagina, setPagina] = useState(0)
  const [rep, setRep] = useState(null)
  const [error, setError] = useState('')

  const params = { gestion, ...filtros, comparar: reporte === 'movimientos' ? '' : comparar }

  useEffect(() => setPagina(0), [reporte, gestion, filtros])
  useEffect(() => {
    setError('')
    const extra = reporte === 'movimientos' ? { limite: POR_PAGINA, offset: pagina * POR_PAGINA } : {}
    let vigente = true // descarta respuestas de consultas anteriores que lleguen tarde
    api(`/reportes/${reporte}?${qs({ ...params, ...extra })}`)
      .then((r) => vigente && setRep(r))
      .catch((e) => vigente && setError(e.message))
    return () => { vigente = false }
  }, [reporte, gestion, filtros, comparar, pagina])

  const exportar = (formato) => descargar(`/reportes/${reporte}/export?${qs({ ...params, formato })}`, `${reporte}_${gestion}.${formato}`)
  const otras = catalogos.gestiones.filter((g) => g !== gestion)

  return (
    <div className="page">
      <div className="tabs">
        {catalogos.reportes.map((r) => (
          <button key={r.id} className={reporte === r.id ? 'active' : ''} onClick={() => { setRep(null); setReporte(r.id) }}>{(t => t[0].toUpperCase() + t.slice(1))(r.titulo.replace('Ejecución por ', ''))}</button>
        ))}
      </div>
      <div className="page-head">
        <h2>{catalogos.reportes.find((r) => r.id === reporte)?.titulo} · {gestion}</h2>
        <div className="acciones">
          {reporte !== 'movimientos' && otras.length > 0 && (
            <select value={comparar} onChange={(e) => setComparar(e.target.value)}>
              <option value="">Sin comparativo</option>
              {otras.map((g) => <option key={g} value={g}>Comparar con {g}</option>)}
            </select>
          )}
          <button onClick={() => exportar('xlsx')}>⬇ Excel</button>
          <button onClick={() => exportar('pdf')}>⬇ PDF</button>
        </div>
      </div>
      <Filtros catalogos={catalogos} valor={filtros} onChange={setFiltros} />
      {error && <div className="error">{error}</div>}
      {rep && rep.reporte === reporte && (
        reporte === 'movimientos'
          ? <TablaMovimientos rep={rep} pagina={pagina} setPagina={setPagina} />
          : <TablaEjecucion key={reporte} rep={rep} comparar={rep.total.comparativo ? Number(comparar) : null} />
      )}
    </div>
  )
}
