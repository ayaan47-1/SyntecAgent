import React from 'react';
import { createRoot } from 'react-dom/client';
import SyntecChatWidget from './SyntecChatWidget';

let container = document.getElementById('syntec-chat-widget-root');
if (!container) {
  container = document.createElement('div');
  container.id = 'syntec-chat-widget-root';
  document.body.appendChild(container);
}

const root = createRoot(container);
root.render(
  <React.StrictMode>
    <SyntecChatWidget />
  </React.StrictMode>
);
