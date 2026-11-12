import { useEffect, useState } from 'react'
import { api } from '../api'

const ROLES = [
  ['consulta', 'Consulta', 've el dashboard y los reportes'],
  ['validador', 'Validador', 'carga el Excel y valida filas'],
  ['admin', 'Administrador', 'gestiona usuarios y auditoría'],
]

export default function Admin({ yo }) {
  const [usuarios, setUsuarios] = useState([])
  const [auditoria, setAuditoria] = useState([])
  const [nuevo, setNuevo] = useState({ username: '', nombre: '', password: '', rol: 'consulta' })
  const [error, setError] = useState('')

  const cargar = () => {
    api('/usuarios').then(setUsuarios)
    api('/auditoria').then(setAuditoria)
  }
  useEffect(cargar, [])

  const crear = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api('/usuarios', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(nuevo) })
      setNuevo({ username: '', nombre: '', password: '', rol: 'consulta' })
      cargar()
    } catch (err) {
      setError(err.message)
    }
  }
  const actualizar = async (id, cambios) => {
    setError('')
    try {
      await api(`/usuarios/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cambios) })
      cargar()
    } catch (err) {
      setError(err.message)
    }
  }
  const campo = (k) => ({ value: nuevo[k], onChange: (e) => setNuevo({ ...nuevo, [k]: e.target.value }) })

  return (
    <div className="page">
      <h2>Administración</h2>
      <div className="grid2">
        <section className="card">
          <h3>Usuarios y roles</h3>
          <table>
            <thead><tr><th>Usuario</th><th>Nombre</th><th>Rol</th><th>Estado</th></tr></thead>
            <tbody>
              {usuarios.map((u) => (
                <tr key={u.id} className={u.activo ? '' : 'inactivo'}>
                  <td>{u.username}</td><td className="txt">{u.nombre}</td>
                  <td>
                    <select value={u.rol} disabled={u.username === yo?.username} onChange={(e) => actualizar(u.id, { rol: e.target.value })}>
                      {ROLES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
                    </select>
                  </td>
                  <td><button className="link" disabled={u.username === yo?.username} onClick={() => actualizar(u.id, { activo: !u.activo })}>{u.activo ? 'Activo · desactivar' : 'Inactivo · activar'}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          <form onSubmit={crear} className="form-inline">
            <input placeholder="usuario" {...campo('username')} required />
            <input placeholder="nombre" {...campo('nombre')} required />
            <input placeholder="contraseña" type="password" {...campo('password')} required />
            <select {...campo('rol')}>{ROLES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
            <button className="primary">Crear</button>
          </form>
          {error && <div className="error">{error}</div>}
          <div className="roles-ayuda small">
            <strong>Separación de funciones</strong>
            <ul>{ROLES.map(([k, l, d]) => <li key={k}><b>{l}:</b> {d}</li>)}</ul>
            <span className="muted">Quien se registra entra como Consulta; solo el administrador asigna otros roles.</span>
          </div>
        </section>
        <section className="card">
          <h3>Registro de auditoría</h3>
          <div className="tabla-wrap alto">
            <table>
              <thead><tr><th>Fecha</th><th>Usuario</th><th>Acción</th><th>Detalle</th></tr></thead>
              <tbody>
                {auditoria.map((a) => (
                  <tr key={a.id}><td>{a.fecha.slice(0, 19).replace('T', ' ')}</td><td>{a.usuario}</td><td>{a.accion}</td>
                    <td className="txt small">{a.detalle ? JSON.stringify(a.detalle) : ''}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  )
}
