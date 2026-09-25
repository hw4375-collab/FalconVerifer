import { MotionConfig } from 'motion/react'
import { lazy, Suspense, useEffect } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { Footer } from './components/Footer'
import { Nav } from './components/Nav'
import { Story } from './pages/Story'

const Demo = lazy(() => import('./pages/Demo'))
const Results = lazy(() => import('./pages/Results'))

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}

// Links from the previous UI: /?trace=<run>/<id> replays, /benchmark is now /results
function Home() {
  const { search } = useLocation()
  return new URLSearchParams(search).has('trace') ? <Navigate to={`/demo${search}`} replace /> : <Story />
}

export function App() {
  const { pathname } = useLocation()
  const fullHeight = pathname === '/demo'
  return (
    <MotionConfig reducedMotion="user">
      <ScrollToTop />
      <Nav />
      <Suspense fallback={<div className="min-h-[70dvh]" />}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/demo" element={<Demo />} />
          <Route path="/results" element={<Results />} />
          <Route path="/benchmark" element={<Navigate to="/results" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
      {!fullHeight && <Footer />}
    </MotionConfig>
  )
}
