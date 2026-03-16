import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { StackProvider, StackTheme, StackClientApp } from '@stackframe/stack'
import './index.css'
import App from './App.jsx'

const stackApp = new StackClientApp({
  projectId: import.meta.env.VITE_STACK_PROJECT_ID || 'your_stack_project_id',
  publishableClientKey: import.meta.env.VITE_STACK_PUBLISHABLE_CLIENT_KEY || 'your_stack_publishable_key',
  tokenStore: 'cookie',
  urls: {
    signIn: '/sign-in',
    signUp: '/sign-up',
    afterSignIn: '/dashboard',
    afterSignUp: '/dashboard',
  },
})

// Expose to api.js for token retrieval
window.__stackClientApp = stackApp

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <StackProvider app={stackApp}>
      <StackTheme>
        <App />
      </StackTheme>
    </StackProvider>
  </StrictMode>,
)
