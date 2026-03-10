import React, { useState, useRef, useEffect } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ConfirmationModal from './ConfirmationModal';
import './ChatInterface.css';

const WELCOME = {
  role: 'assistant',
  content:
    'SYNTEC BIM Agent online. I can query, add, update, and delete building classification codes.\n\nTry: *"list all categories starting with 03"* or *"what is code 04 05 13.A1?"*',
};

function ChatInterface() {
  const [messages, setMessages] = useState([WELCOME]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [pendingAction, setPendingAction] = useState(null);
  const [isConfirming, setIsConfirming] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const API_URL = import.meta.env.VITE_API_URL || '/api';

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDarkMode ? 'dark' : 'light');
  }, [isDarkMode]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userMessage, source: 'agent' }),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();

      if (data.pending_action) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.answer,
          isActionPrompt: true,
        }]);
        setPendingAction(data.pending_action);
        return;
      }

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        isActionResult: !!data.action_result,
      }]);
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Connection error: ${error.message}. Please ensure the backend is running.`,
        isError: true,
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmAction = async (editedParams) => {
    if (!pendingAction) return;
    setIsConfirming(true);
    const actionToConfirm = editedParams
      ? { ...pendingAction, params: editedParams }
      : pendingAction;
    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: '', source: 'agent', confirm_action: actionToConfirm }),
      });
      const data = await response.json();
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        isActionResult: true,
      }]);
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${error.message}`,
        isError: true,
      }]);
    } finally {
      setPendingAction(null);
      setIsConfirming(false);
    }
  };

  const handleCancelAction = () => {
    setMessages(prev => [...prev, { role: 'assistant', content: 'Action cancelled.' }]);
    setPendingAction(null);
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-brand">
          <span className="brand-mark">◈</span>
          <div className="brand-text">
            <span className="brand-name">SYNTEC AGENT</span>
            <span className="brand-sub">BIM Classification Management</span>
          </div>
        </div>
        <div className="header-controls">
          <div className="status-badge">
            <span className="status-dot" />
            <span>LIVE</span>
          </div>
          <button
            className="theme-toggle"
            onClick={() => setIsDarkMode(d => !d)}
            aria-label="Toggle theme"
          >
            {isDarkMode ? (
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="5" />
                <line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" />
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                <line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" />
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
              </svg>
            ) : (
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
            )}
          </button>
        </div>
      </header>

      <main className="messages-area">
        <div className="messages-inner">
          {messages.map((msg, idx) => (
            <MessageRow key={idx} message={msg} />
          ))}
          {isLoading && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>
      </main>

      <ConfirmationModal
        pendingAction={pendingAction}
        onConfirm={handleConfirmAction}
        onCancel={handleCancelAction}
        isConfirming={isConfirming}
      />

      <footer className="input-bar">
        <form onSubmit={handleSubmit} className="input-form">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            placeholder="Query classifications, add codes, update entries..."
            className="input-field"
            disabled={isLoading}
            autoComplete="off"
          />
          <button
            type="submit"
            className="send-btn"
            disabled={isLoading || !inputValue.trim()}
            aria-label="Send"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </form>
      </footer>
    </div>
  );
}

function MessageRow({ message }) {
  const isUser = message.role === 'user';
  return (
    <div className={`msg-row ${isUser ? 'msg-row--user' : 'msg-row--agent'}`}>
      {!isUser && <div className="msg-avatar">◈</div>}
      <div className={[
        'msg-bubble',
        isUser ? 'msg-bubble--user' : 'msg-bubble--agent',
        message.isError ? 'msg-bubble--error' : '',
        message.isActionResult ? 'msg-bubble--success' : '',
      ].filter(Boolean).join(' ')}>
        <Markdown
          remarkPlugins={[remarkGfm]}
          components={{
            pre({ children }) {
              return <pre className="code-block">{children}</pre>;
            },
            code({ className, children, ...props }) {
              return <code className={className ?? 'inline-code'} {...props}>{children}</code>;
            },
            table({ children }) {
              return <div className="table-wrap"><table>{children}</table></div>;
            },
          }}
        >
          {message.content}
        </Markdown>
        {message.isActionResult && (
          <div className="result-badge result-badge--success">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            Action completed
          </div>
        )}
        {message.isActionPrompt && (
          <div className="result-badge result-badge--warning">⚠ Awaiting confirmation</div>
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="msg-row msg-row--agent">
      <div className="msg-avatar">◈</div>
      <div className="typing-indicator">
        <span /><span /><span />
      </div>
    </div>
  );
}

export default ChatInterface;
