/**
 * React 18 Application Entry Point
 * Initializes Sentry error tracking (if configured) and renders App component.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { initSentry } from './lib/sentry';
import './styles/index.css';

// Initialize Sentry for error tracking if DSN is configured
void initSentry();

const root = document.getElementById('root');
if (!root) {
  throw new Error('Root element not found');
}

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
