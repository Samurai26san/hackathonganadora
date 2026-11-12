import { useEffect, useState } from 'react'
import { api, getToken, setToken } from './api'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Reportes from './pages/Reportes'
import Importar from './pages/Importar'
import Admin from './pages/Admin'
import Validacion from './pages/Validacion'

// Separación de funciones: cada rol ve solo lo que le corresponde
const PAGINAS = [
  { id: 'dashboard', label: 'Dashboard', roles: ['validador', 'consulta'] },
  { id: 'reportes', label: 'Reportes', roles: ['validador', 'consulta'] },
  { id: 'importar', label: 'Cargar datos', roles: ['validador'] },
  { id: 'validacion', label: 'Validación de datos', roles: ['validador'] },
  { id: 'admin', label: 'Usuarios y auditoría', roles: ['admin'] },
]
const NOMBRE_ROL = { admin: 'Administrador', validador: 'Validador', consulta: 'Consulta' }
const veDatos = (rol) => rol !== 'admin'

export default function App() {
  const [usuario, setUsuario] = useState(null)
  const [cargando, setCargando] = useState(!!getToken())
  const [pagina, setPagina] = useState('dashboard')
  const [catalogos, setCatalogos] = useState(null)
  const [gestion, setGestion] = useState(null)
  const [presentacion, setPresentacion] = useState(false)

  // Modo presentación: pantalla completa sin barra lateral
  const alternarPresentacion = () => {
    const activar = !presentacion
    setPresentacion(activar)
    if (activar) document.documentElement.requestFullscreen?.().catch(() => {})
    else if (document.fullscreenElement) document.exitFullscreen?.()
  }
  useEffect(() => {
    const salir = () => !document.fullscreenElement && setPresentacion(false)
    document.addEventListener('fullscreenchange', salir)
    return () => document.removeEventListener('fullscreenchange', salir)
  }, [])

  useEffect(() => {
    if (!getToken()) return
    api('/auth/me').then(setUsuario).finally(() => setCargando(false))
  }, [])

  const recargarCatalogos = () =>
    api('/catalogos').then((c) => {
      setCatalogos(c)
      setGestion((g) => g ?? c.gestiones[0] ?? new Date().getFullYear())
    })

  useEffect(() => {
    if (!usuario) return
    // Cada rol entra a su primera página permitida; el admin no consulta datos financieros
    setPagina(PAGINAS.find((p) => p.roles.includes(usuario.rol))?.id)
    if (veDatos(usuario.rol)) recargarCatalogos()
  }, [usuario])

  if (cargando) return null
  if (!usuario) return <Login onLogin={(u) => setUsuario(u)} />

  const salir = () => {
    setToken(null)
    setUsuario(null)
    setCatalogos(null)
    setGestion(null)
  }

  return (
    <div className={presentacion ? 'layout presentacion' : 'layout'}>
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">Bs</span>
          <div>
            <strong>Control Presupuestario</strong>
            <small>Ejecución financiera</small>
          </div>
        </div>
        <nav>
          {PAGINAS.filter((p) => p.roles.includes(usuario.rol)).map((p) => (
            <button key={p.id} className={pagina === p.id ? 'active' : ''} onClick={() => setPagina(p.id)}>
              {p.label}
            </button>
          ))}
        </nav>
        <div className="user">
          <div>
            <strong>{usuario.nombre}</strong>
            <small>{NOMBRE_ROL[usuario.rol] || usuario.rol}</small>
          </div>
          <button className="link" onClick={salir}>Salir</button>
        </div>
      </aside>
      <main>
        {catalogos && (
          <header className="topbar">
            <label>
              Gestión
              <select value={gestion ?? ''} onChange={(e) => setGestion(Number(e.target.value))}>
                {catalogos.gestiones.map((g) => <option key={g}>{g}</option>)}
              </select>
            </label>
          </header>
        )}
        {catalogos && gestion && (
          <>
            {pagina === 'dashboard' && (
              <Dashboard gestion={gestion} catalogos={catalogos} puedeValidar={usuario.rol === 'validador'}
                presentacion={presentacion} onPresentacion={alternarPresentacion} irA={setPagina} />
            )}
            {pagina === 'reportes' && <Reportes gestion={gestion} catalogos={catalogos} />}
            {pagina === 'importar' && <Importar onImportado={recargarCatalogos} irA={setPagina} />}
            {pagina === 'validacion' && <Validacion gestion={gestion} onValidado={recargarCatalogos} />}
          </>
        )}
        {pagina === 'admin' && <Admin yo={usuario} />}
      </main>
    </div>
  )
}
