import { useEffect, useState } from 'react'

interface HealthResponse {
  status: string
}

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/health')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: HealthResponse) => setHealth(data))
      .catch((err: Error) => setError(err.message))
  }, [])

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', padding: '2rem', maxWidth: 600, margin: '0 auto' }}>
      <h1>Recon Dashboard</h1>
      <h2>Backend Health</h2>
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}
      {health && <p style={{ color: 'green' }}>Status: {health.status}</p>}
      {!health && !error && <p>Loading...</p>}
    </div>
  )
}

export default App
