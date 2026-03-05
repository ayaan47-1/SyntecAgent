import React, { useState, useRef, useEffect } from 'react';
import Markdown from 'react-markdown';
import './SyntecChatWidget.css';

function SyntecChatWidget() {
  const [isOpen, setIsOpen] = useState(true);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);
  const [isConfirming, setIsConfirming] = useState(false);
  const messagesEndRef = useRef(null);

  const API_URL = window.SYNTEC_WIDGET_API_URL || (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL) || 'http://localhost:5001/api';

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    setMessages([
      {
        role: 'assistant',
        content: 'Welcome to Syntec Group. How can I assist you with BuildUSA, architecture, or construction inquiries today?'
      }
    ]);
  }, []);

  const handleOpenWidget = () => {
    setIsOpen(true);
  };

  const handleCloseWidget = () => {
    setIsOpen(false);
  };

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
        body: JSON.stringify({ question: userMessage, source: 'agent' })
      });

      if (!response.ok) {
        throw new Error(`Failed to get response: ${response.status}`);
      }

      const data = await response.json();
      if (data.pending_action) {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: data.answer, isActionPrompt: true }
        ]);
        setPendingAction(data.pending_action);
        return;
      }

      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: data.answer,
          sources: data.sources,
          followUpQuestions: data.follow_up_questions,
          isActionResult: !!data.action_result
        }
      ]);
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${error.message}. Please try again.`
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFollowUpClick = (question) => {
    setInputValue(question);
    handleSubmit({ preventDefault: () => {} });
  };

  const handleConfirmAction = async () => {
    if (!pendingAction) return;
    setIsConfirming(true);
    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: '', source: 'agent', confirm_action: pendingAction })
      });
      const data = await response.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.answer, isActionResult: true }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${error.message}` }]);
    } finally {
      setPendingAction(null);
      setIsConfirming(false);
    }
  };

  const handleCancelAction = () => {
    setMessages(prev => [...prev, { role: 'assistant', content: 'Action cancelled.' }]);
    setPendingAction(null);
  };

  const ChatIcon = () => (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );

  const CloseIcon = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );

  const SendIcon = () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M2 21l21-9L2 3v7l15 2-15 2v7z" />
    </svg>
  );

  const MoonIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );

  const SunIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5" />
      <line x1="12" y1="1" x2="12" y2="3" />
      <line x1="12" y1="21" x2="12" y2="23" />
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
      <line x1="1" y1="12" x2="3" y2="12" />
      <line x1="21" y1="12" x2="23" y2="12" />
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
    </svg>
  );

  const SOURCE_COLORS = [
    '#41C5EB', '#637a80', '#2F2F2F', '#868087', '#41C5EB',
    '#637a80', '#2F2F2F', '#868087'
  ];

  const getSourceAbbrev = (src) => {
    const name = (src.source || src || '').replace(/\.[^/.]+$/, '');
    const words = name.replace(/[_\-/\\]+/g, ' ').trim().split(/\s+/);
    if (words.length >= 2) {
      return words.slice(0, 3).map(w => w[0]).join('').toUpperCase();
    }
    return name.slice(0, 3).toUpperCase();
  };

  const getSourceColor = (src, idx) => SOURCE_COLORS[idx % SOURCE_COLORS.length];

  const lastMessage = messages[messages.length - 1];
  const showFollowUps = lastMessage?.role === 'assistant' && lastMessage?.followUpQuestions?.length > 0;

  return (
    <div className={`sw-container${darkMode ? ' sw-dark' : ''}`}>
      {!isOpen && (
        <button className="sw-button" onClick={handleOpenWidget} aria-label="Open chat">
          <ChatIcon />
        </button>
      )}

      {isOpen && (
        <div className="sw-chat-window">
          <div className="sw-header">
            <div className="sw-header-title">
              <span className="sw-header-text">SyntecAI</span>
              <span className="sw-status-dot" />
            </div>
            <div className="sw-header-actions">
              <button className="sw-theme-btn" onClick={() => setDarkMode(!darkMode)} aria-label="Toggle dark mode">
                {darkMode ? <SunIcon /> : <MoonIcon />}
              </button>
              <button className="sw-close-btn" onClick={handleCloseWidget} aria-label="Close chat">
                <CloseIcon />
              </button>
            </div>
          </div>

          <div className="sw-messages">
            {messages.map((msg, idx) => (
              <div key={idx} className={`sw-message sw-message-${msg.role}`}>
                <div className="sw-message-content">
                  <Markdown>{msg.content}</Markdown>
                  {msg.isActionResult && (
                    <span className="sw-action-badge">Action completed</span>
                  )}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="sw-sources">
                      {msg.sources.map((src, i) => (
                        <span
                          key={i}
                          className="sw-source-icon"
                          style={{ background: getSourceColor(src, i) }}
                          title={src.source || src}
                        >
                          {getSourceAbbrev(src)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="sw-message sw-message-assistant">
                <div className="sw-message-content">
                  <div className="sw-typing">
                    <span />
                    <span />
                    <span />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {showFollowUps && !isLoading && (
            <div className="sw-follow-ups">
              {lastMessage.followUpQuestions.slice(0, 3).map((question, idx) => (
                <button
                  key={idx}
                  className="sw-follow-up-btn"
                  onClick={() => handleFollowUpClick(question)}
                >
                  {question}
                </button>
              ))}
            </div>
          )}

          {pendingAction && (
            <div className="sw-confirm-bar">
              <p className="sw-confirm-text">{pendingAction.description}</p>
              <div className="sw-confirm-buttons">
                <button className="sw-confirm-cancel" onClick={handleCancelAction} disabled={isConfirming}>Cancel</button>
                <button className="sw-confirm-ok" onClick={handleConfirmAction} disabled={isConfirming}>
                  {isConfirming ? '...' : 'Confirm'}
                </button>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="sw-input-form">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask a question..."
              className="sw-input"
              disabled={isLoading}
            />
            <div className="sw-input-actions">
              <button
                type="submit"
                className="sw-send-btn"
                disabled={isLoading || !inputValue.trim()}
                aria-label="Send message"
              >
                <SendIcon />
              </button>
            </div>
          </form>

          <div className="sw-footer">
            Powered by Syntec Group
          </div>
        </div>
      )}
    </div>
  );
}

export default SyntecChatWidget;
