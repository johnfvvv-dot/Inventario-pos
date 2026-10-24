import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';
import { registerServiceWorker, unregister } from './serviceWorker';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// PWA: solo se registra en producción. En desarrollo se desregistra para
// evitar que el navegador sirva una versión vieja del frontend desde caché.
if (process.env.NODE_ENV === 'production') {
  registerServiceWorker();
} else {
  unregister();
}