import { useState } from 'react'
import { setToken } from '../api'

export default function Login({ onLogin }) {
  const [modo, setModo] = useState('ingresar')
  const [form, setForm] = useState({ username: '', password: '', nombre: '', confirmar: '' })
  const [error, setError] = useState('')
  const registro = modo === 'registro'
  const campo = (k) => ({ value: form[k], onChange: (e) => setForm({ ...form, [k]: e.target.value }) })

  const enviar = async (e) => {
    e.preventDefault()
    setError('')
    if (registro && form.password !== form.confirmar) return setError('Las contraseñas no coinciden')
    const res = registro
      ? await fetch('/api/auth/registro', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: form.username, nombre: form.nombre, password: form.password }),
        })
      : await fetch('/api/auth/login', { method: 'POST', body: new URLSearchParams({ username: form.username, password: form.password }) })
    const data = await res.json()
    if (!res.ok) return setError(data.detail || 'No se pudo completar la operación')
    setToken(data.access_token)
    onLogin(data.usuario)
  }

  return (
    <div className="login">
      <form onSubmit={enviar} className="card">
        <h1>Control Presupuestario</h1>
        <p className="muted">{registro ? 'Crear una cuenta de consulta' : 'Sistema de ejecución financiera'}</p>
        {registro && <label>Nombre completo<input {...campo('nombre')} required /></label>}
        <label>Usuario<input {...campo('username')} autoFocus required /></label>
        <label>Contraseña<input type="password" {...campo('password')} required /></label>
        {registro && <label>Confirmar contraseña<input type="password" {...campo('confirmar')} required /></label>}
        {error && <div className="error">{error}</div>}
        <button className="primary">{registro ? 'Crear cuenta' : 'Ingresar'}</button>
        <button type="button" className="link" onClick={() => { setModo(registro ? 'ingresar' : 'registro'); setError('') }}>
          {registro ? '¿Ya tienes cuenta? Ingresar' : '¿No tienes cuenta? Regístrate'}
        </button>
        {registro && <p className="muted small">Las cuentas nuevas tienen rol de Consulta (dashboard y reportes). El administrador puede asignarte el rol de Validador.</p>}
      </form>
    </div>
  )
}
