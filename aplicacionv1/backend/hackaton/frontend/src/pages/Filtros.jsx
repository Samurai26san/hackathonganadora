import { useState } from 'react'

const DIMS = [
  ['financiador', 'Financiador'],
  ['rubro', 'Rubro'],
  ['cuenta', 'Cuenta'],
  ['area', 'Área'],
  ['region', 'Región'],
  ['mes', 'Mes'],
]

// Filtros combinados: cada dimensión admite selección múltiple.
export default function Filtros({ catalogos, valor, onChange, ocultar = [] }) {
  const [abierto, setAbierto] = useState(null)
  const toggle = (dim, id) => {
    const actual = valor[dim] || []
    onChange({ ...valor, [dim]: actual.includes(id) ? actual.filter((x) => x !== id) : [...actual, id] })
  }
  const opciones = (dim) => {
    if (dim === 'cuenta' && valor.rubro?.length) return catalogos.cuenta.filter((c) => valor.rubro.includes(c.rubro_id))
    return catalogos[dim]
  }
  const activos = Object.values(valor).some((v) => v?.length)

  return (
    <div className="filtros">
      {DIMS.filter(([d]) => !ocultar.includes(d)).map(([dim, label]) => {
        const sel = valor[dim] || []
        return (
          <div key={dim} className="filtro">
            <button className={sel.length ? 'chip on' : 'chip'} onClick={() => setAbierto(abierto === dim ? null : dim)}>
              {label}{sel.length ? ` (${sel.length})` : ''} ▾
            </button>
            {abierto === dim && (
              <div className="pop" onMouseLeave={() => setAbierto(null)}>
                {opciones(dim).map((o) => (
                  <label key={o.id}>
                    <input type="checkbox" checked={sel.includes(o.id)} onChange={() => toggle(dim, o.id)} />
                    {dim === 'mes' ? o.nombre : `${o.codigo} - ${o.nombre}`}
                  </label>
                ))}
              </div>
            )}
          </div>
        )
      })}
      {activos && <button className="link" onClick={() => onChange({})}>Limpiar filtros</button>}
    </div>
  )
}
