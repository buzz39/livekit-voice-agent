import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { StackProvider, StackTheme, StackClientApp } from '@stackframe/react'
import './index.css'
import App from './App.jsx'

const stackProjectId = import.meta.env.VITE_STACK_PROJECT_ID;
if (!stackProjectId) {
  console.warn('VITE_STACK_PROJECT_ID is not set. Auth will not work until configured.');
}

const stackApp = new StackClientApp({
  projectId: stackProjectId || 'placeholder',
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
