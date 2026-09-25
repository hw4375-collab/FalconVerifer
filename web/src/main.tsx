import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, MemoryRouter } from 'react-router-dom'
import { App } from './App'
import { LangProvider } from './i18n'
import './styles.css'

// VITE_STATIC builds a single self-contained page with no server behind it (see vite.config.ts)
const Router = import.meta.env.VITE_STATIC === '1' ? MemoryRouter : BrowserRouter

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Router>
      <LangProvider>
        <App />
      </LangProvider>
    </Router>
  </StrictMode>,
)
