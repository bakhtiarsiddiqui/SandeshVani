import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource/mukta/400.css'
import '@fontsource/mukta/500.css'
import '@fontsource/mukta/600.css'
import '@fontsource/mukta/700.css'
import '@fontsource/mukta/800.css'
import './index.css'
import App from './App.jsx'
import PointerGlow from './components/fx/PointerGlow.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <PointerGlow />
    <App />
  </StrictMode>,
)

