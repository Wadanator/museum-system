import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { SocketProvider } from './context/SocketContext.jsx'
import { AuthProvider } from './context/AuthContext.jsx'
import { ConfirmProvider } from './context/ConfirmContext.jsx'
import App from './App.jsx'

import './index.css'
import './styles/base.css'
import './styles/layout.css'
import './styles/controls.css'
import './styles/utilities.css'
import './styles/feedback.css'

// --- NOVÉ IMPORTY PODĽA POHĽADOV ---
import './styles/views/main-dashboard.css'
import './styles/views/stats-view.css'
import './styles/views/logs-view.css'
import './styles/views/resources-view.css'
import './styles/views/main-dashboard.css'

import 'prismjs/themes/prism.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <SocketProvider>
          <ConfirmProvider>
            <App />
          </ConfirmProvider>
        </SocketProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)