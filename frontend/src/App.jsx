import { useState } from "react"

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000"

function App() {
  const [inputUrl, setInputUrl] = useState("")
  const [shortUrl, setShortUrl] = useState("")
  const [shortCode, setShortCode] = useState("")
  const [clicks, setClicks] = useState(null)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)

  async function handleShorten() {
    setError("")
    setShortUrl("")
    setClicks(null)
    setLoading(true)

    try {
      const response = await fetch(`${API_BASE}/api/shorten`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: inputUrl }),
      })

      if (!response.ok) {
        const data = await response.json()
        setError(data.detail || "Something went wrong")
        return
      }

      const data = await response.json()
      setShortUrl(data.short_url)
      setShortCode(data.short_code)
    } catch {
      setError("Could not connect to server. Is FastAPI running?")
    } finally {
      setLoading(false)
    }
  }

  async function handleStats() {
    setError("")
    setClicks(null)

    try {
      const response = await fetch(`${API_BASE}/api/stats/${shortCode}`)

      if (!response.ok) {
        setError("Could not fetch stats")
        return
      }

      const data = await response.json()
      setClicks(data.clicks)
    } catch {
      setError("Could not connect to server")
    }
  }

  function handleCopy() {
    navigator.clipboard.writeText(shortUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="card">
      <h1>URL Shortener</h1>
      <p className="subtitle">Paste a long URL and get a short link instantly</p>

      <input
        type="text"
        placeholder="https://example.com/very/long/url"
        value={inputUrl}
        onChange={(e) => setInputUrl(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleShorten()}
      />

      <button
        className="btn"
        onClick={handleShorten}
        disabled={loading || !inputUrl}
      >
        {loading ? "Shortening..." : "Shorten"}
      </button>

      {error && <div className="error">{error}</div>}

      {shortUrl && (
        <>
          <div className="result-box">
            <div className="result-label">Your short link</div>
            <div className="result-url">
              <a href={shortUrl} target="_blank" rel="noreferrer">
                {shortUrl}
              </a>
            </div>
            <button className="btn copy-btn" onClick={handleCopy}>
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>

          <div className="divider" />

          <button className="btn btn-outline" onClick={handleStats}>
            Check Stats
          </button>

          {clicks !== null && (
            <div className="stats-box">
              <div className="stats-clicks">{clicks}</div>
              <div className="stats-label">total clicks</div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default App
