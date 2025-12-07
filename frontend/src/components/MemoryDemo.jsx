import React, { useState } from 'react';
import ChatService from '../services/ChatService';

const MemoryDemo = () => {
  const [message, setMessage] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [enableMemory, setEnableMemory] = useState(false);
  const [conversation, setConversation] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [messageCount, setMessageCount] = useState(0);
  const [rememberedInfo, setRememberedInfo] = useState({
    name: null,
    persona: null
  });

  const chatService = new ChatService();

  const extractUserInfo = (text) => {
    const updated = { ...rememberedInfo };
    
    // Extract name
    const namePatterns = [
      /my name is (\w+)/i,
      /i'm (\w+)/i,
      /i am (\w+)/i,
      /call me (\w+)/i
    ];
    
    for (const pattern of namePatterns) {
      const match = text.match(pattern);
      if (match && match[1]) {
        updated.name = match[1];
        break;
      }
    }
    
    // Extract persona
    const personaPatterns = [
      /i'm a (\w+)/i,
      /i am a (\w+)/i,
      /i work as a? (\w+)/i,
      /i'm an? (\w+)/i
    ];
    
    for (const pattern of personaPatterns) {
      const match = text.match(pattern);
      if (match && match[1]) {
        updated.persona = match[1];
        break;
      }
    }
    
    setRememberedInfo(updated);
  };

  const handleSendMessage = async () => {
    if (!message.trim()) return;

    setLoading(true);
    setError(null);

    // Extract info if memory enabled
    if (enableMemory) {
      extractUserInfo(message);
    }

    // Add user message to conversation
    const userMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toLocaleTimeString()
    };
    setConversation(prev => [...prev, userMessage]);
    setMessageCount(prev => prev + 1);

    try {
      // Send message with memory flag
      const response = await chatService.sendMessage(
        message,
        sessionId,
        ['generic_agent'],
        null,
        null,
        enableMemory  // Pass memory flag
      );

      // Add assistant response to conversation
      const assistantMessage = {
        role: 'assistant',
        content: response.content,
        agent: response.agent,
        timestamp: new Date(response.timestamp).toLocaleTimeString(),
        memoryEnabled: enableMemory
      };
      setConversation(prev => [...prev, assistantMessage]);
      setMessageCount(prev => prev + 1);

      // Save session ID for continuity
      if (response.sessionId) {
        setSessionId(response.sessionId);
      }

      setMessage('');
    } catch (err) {
      setError(err.message || 'Failed to send message');
      console.error('Error sending message:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setConversation([]);
    setSessionId(null);
    setMessage('');
    setError(null);
    setMessageCount(0);
    setRememberedInfo({ name: null, persona: null });
  };

  const handleToggleMemory = (checked) => {
    setEnableMemory(checked);
    if (checked) {
      // Reset when enabling memory
      handleReset();
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>?? Long-Running Memory Demo</h2>
        <p style={styles.subtitle}>
          Test UserInfoMemory feature - the agent will remember your name and persona across messages
        </p>
      </div>

      {/* Enhanced Memory Toggle */}
      <div style={{
        ...styles.memoryToggle,
        ...(enableMemory ? styles.memoryToggleActive : {})
      }}>
        <label style={styles.toggleLabel}>
          {/* Custom Toggle Switch */}
          <div style={styles.switch}>
            <input
              type="checkbox"
              checked={enableMemory}
              onChange={(e) => handleToggleMemory(e.target.checked)}
              style={styles.switchInput}
            />
            <span style={{
              ...styles.slider,
              ...(enableMemory ? styles.sliderActive : {})
            }}>
              <span style={{
                ...styles.sliderBall,
                ...(enableMemory ? styles.sliderBallActive : {})
              }}></span>
            </span>
          </div>
          <div style={styles.toggleStatus}>
            <span style={styles.statusIcon}>
              {enableMemory ? '??' : '??'}
            </span>
            <span style={styles.toggleText}>
              {enableMemory ? 'Memory Enabled' : 'Memory Disabled'}
            </span>
          </div>
        </label>
        {enableMemory && (
          <div style={styles.memoryInfo}>
            <div style={styles.memoryInfoText}>
              ?? The agent will extract and remember your name and persona from your messages
            </div>
            <div style={styles.memoryStats}>
              <div style={styles.statItem}>
                <span style={styles.statLabel}>Name:</span>
                <span style={styles.statValue}>{rememberedInfo.name || 'Not set'}</span>
              </div>
              <div style={styles.statItem}>
                <span style={styles.statLabel}>Persona:</span>
                <span style={styles.statValue}>{rememberedInfo.persona || 'Not set'}</span>
              </div>
              <div style={styles.statItem}>
                <span style={styles.statLabel}>Messages:</span>
                <span style={styles.statValue}>{messageCount}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Session Info */}
      {sessionId && (
        <div style={styles.sessionInfo}>
          <span style={styles.sessionLabel}>Session:</span>
          <span style={styles.sessionId}>{sessionId.substring(0, 8)}...</span>
          <button onClick={handleReset} style={styles.resetButton}>
            Reset Session
          </button>
        </div>
      )}

      {/* Conversation */}
      <div style={styles.conversation}>
        {conversation.length === 0 ? (
          <div style={styles.emptyState}>
            <p style={styles.emptyText}>
              {enableMemory 
                ? "Try saying: 'My name is John' or 'I'm a software developer'"
                : "Start a conversation (memory disabled)"}
            </p>
          </div>
        ) : (
          conversation.map((msg, index) => (
            <div
              key={index}
              style={{
                ...styles.message,
                ...(msg.role === 'user' ? styles.userMessage : styles.assistantMessage)
              }}
            >
              <div style={styles.messageHeader}>
                <span style={styles.messageRole}>
                  {msg.role === 'user' ? '?? You' : `?? ${msg.agent || 'Assistant'}`}
                </span>
                <span style={styles.messageTime}>{msg.timestamp}</span>
                {msg.memoryEnabled !== undefined && (
                  <span style={styles.memoryBadge}>
                    {msg.memoryEnabled ? '?? Memory' : '?? No Memory'}
                  </span>
                )}
              </div>
              <div style={styles.messageContent}>{msg.content}</div>
            </div>
          ))
        )}
        {loading && (
          <div style={styles.loading}>
            <div style={styles.loadingSpinner}></div>
            <span>Thinking...</span>
          </div>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div style={styles.error}>
          ?? {error}
        </div>
      )}

      {/* Input Area */}
      <div style={styles.inputArea}>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={
            enableMemory
              ? "Tell me your name or describe yourself..."
              : "Type your message..."
          }
          style={styles.textarea}
          disabled={loading}
          rows={3}
        />
        <button
          onClick={handleSendMessage}
          disabled={loading || !message.trim()}
          style={{
            ...styles.sendButton,
            ...(loading || !message.trim() ? styles.sendButtonDisabled : {})
          }}
        >
          {loading ? '? Sending...' : '?? Send'}
        </button>
      </div>

      {/* Tips */}
      {enableMemory && (
        <div style={styles.tips}>
          <h4 style={styles.tipsTitle}>?? Memory Demo Tips:</h4>
          <ul style={styles.tipsList}>
            <li>First, introduce yourself: "My name is [Your Name]"</li>
            <li>Then, share your role: "I'm a [Your Role]"</li>
            <li>Ask questions and see the agent use your information!</li>
            <li>The agent will ask for missing info naturally if needed</li>
            <li>Try resetting and see how memory persists in the session</li>
          </ul>
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    maxWidth: '900px',
    margin: '20px auto',
    padding: '20px',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    backgroundColor: '#f5f7fa',
    borderRadius: '12px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
  },
  header: {
    textAlign: 'center',
    marginBottom: '20px',
    paddingBottom: '15px',
    borderBottom: '2px solid #e0e4e8'
  },
  title: {
    fontSize: '28px',
    fontWeight: '700',
    color: '#2c3e50',
    margin: '0 0 8px 0'
  },
  subtitle: {
    fontSize: '14px',
    color: '#7f8c8d',
    margin: 0
  },
  memoryToggle: {
    backgroundColor: 'white',
    padding: '20px',
    borderRadius: '12px',
    marginBottom: '20px',
    border: '2px solid #e0e4e8',
    transition: 'all 0.3s ease'
  },
  memoryToggleActive: {
    background: 'linear-gradient(135deg, #e7f3ff 0%, #f0e7ff 100%)',
    borderColor: '#667eea'
  },
  toggleLabel: {
    display: 'flex',
    alignItems: 'center',
    cursor: 'pointer',
    fontSize: '18px',
    fontWeight: '600',
    userSelect: 'none'
  },
  switch: {
    position: 'relative',
    display: 'inline-block',
    width: '60px',
    height: '34px',
    marginRight: '15px'
  },
  switchInput: {
    opacity: 0,
    width: 0,
    height: 0
  },
  slider: {
    position: 'absolute',
    cursor: 'pointer',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: '#ccc',
    borderRadius: '34px',
    transition: 'background-color 0.4s'
  },
  sliderActive: {
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
  },
  sliderBall: {
    position: 'absolute',
    height: '26px',
    width: '26px',
    left: '4px',
    bottom: '4px',
    backgroundColor: 'white',
    borderRadius: '50%',
    transition: 'transform 0.4s',
    boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
  },
  sliderBallActive: {
    transform: 'translateX(26px)'
  },
  toggleStatus: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px'
  },
  statusIcon: {
    fontSize: '24px',
    animation: 'pulse 2s ease-in-out infinite'
  },
  toggleText: {
    color: '#2c3e50',
    fontSize: '18px'
  },
  memoryInfo: {
    marginTop: '15px',
    padding: '15px',
    background: '#e7f3ff',
    borderLeft: '4px solid #2196f3',
    borderRadius: '6px',
    animation: 'slideDown 0.3s ease-out'
  },
  memoryInfoText: {
    fontSize: '14px',
    color: '#1976d2',
    marginBottom: '12px'
  },
  memoryStats: {
    display: 'flex',
    gap: '20px',
    padding: '10px',
    background: 'rgba(255,255,255,0.6)',
    borderRadius: '6px',
    flexWrap: 'wrap'
  },
  statItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '13px'
  },
  statLabel: {
    fontWeight: '600',
    color: '#495057'
  },
  statValue: {
    color: '#667eea',
    fontFamily: '"Courier New", monospace',
    fontWeight: '600'
  },
  sessionInfo: {
    backgroundColor: '#fff3cd',
    padding: '10px 15px',
    borderRadius: '6px',
    marginBottom: '15px',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    fontSize: '14px'
  },
  sessionLabel: {
    fontWeight: '600',
    color: '#856404'
  },
  sessionId: {
    fontFamily: 'monospace',
    color: '#856404',
    flex: 1
  },
  resetButton: {
    padding: '6px 12px',
    backgroundColor: '#dc3545',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: '600',
    transition: 'background-color 0.2s'
  },
  conversation: {
    backgroundColor: 'white',
    minHeight: '400px',
    maxHeight: '500px',
    overflowY: 'auto',
    padding: '15px',
    borderRadius: '8px',
    marginBottom: '15px',
    border: '1px solid #e0e4e8'
  },
  emptyState: {
    height: '380px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  emptyText: {
    color: '#95a5a6',
    fontSize: '15px',
    textAlign: 'center'
  },
  message: {
    marginBottom: '15px',
    padding: '12px',
    borderRadius: '8px',
    maxWidth: '85%'
  },
  userMessage: {
    backgroundColor: '#e3f2fd',
    marginLeft: 'auto',
    borderLeft: '4px solid #2196f3'
  },
  assistantMessage: {
    backgroundColor: '#f1f8e9',
    marginRight: 'auto',
    borderLeft: '4px solid #8bc34a'
  },
  messageHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginBottom: '6px',
    fontSize: '13px'
  },
  messageRole: {
    fontWeight: '700',
    color: '#2c3e50'
  },
  messageTime: {
    color: '#95a5a6',
    fontSize: '12px'
  },
  memoryBadge: {
    fontSize: '11px',
    padding: '2px 8px',
    borderRadius: '10px',
    backgroundColor: '#fff',
    border: '1px solid #ddd',
    marginLeft: 'auto'
  },
  messageContent: {
    fontSize: '14px',
    lineHeight: '1.5',
    color: '#34495e',
    whiteSpace: 'pre-wrap'
  },
  loading: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    color: '#7f8c8d',
    padding: '12px',
    fontSize: '14px'
  },
  loadingSpinner: {
    width: '16px',
    height: '16px',
    border: '2px solid #e0e4e8',
    borderTop: '2px solid #3498db',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite'
  },
  error: {
    backgroundColor: '#f8d7da',
    color: '#721c24',
    padding: '12px',
    borderRadius: '6px',
    marginBottom: '15px',
    fontSize: '14px',
    border: '1px solid #f5c6cb'
  },
  inputArea: {
    display: 'flex',
    gap: '10px',
    marginBottom: '15px'
  },
  textarea: {
    flex: 1,
    padding: '12px',
    borderRadius: '8px',
    border: '1px solid #ced4da',
    fontSize: '14px',
    fontFamily: 'inherit',
    resize: 'vertical',
    minHeight: '60px'
  },
  sendButton: {
    padding: '12px 24px',
    backgroundColor: '#28a745',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '15px',
    fontWeight: '600',
    transition: 'background-color 0.2s',
    whiteSpace: 'nowrap'
  },
  sendButtonDisabled: {
    backgroundColor: '#6c757d',
    cursor: 'not-allowed'
  },
  tips: {
    backgroundColor: '#e8f5e9',
    padding: '15px',
    borderRadius: '8px',
    border: '1px solid #c8e6c9'
  },
  tipsTitle: {
    margin: '0 0 10px 0',
    color: '#2e7d32',
    fontSize: '15px'
  },
  tipsList: {
    margin: 0,
    paddingLeft: '20px',
    color: '#388e3c',
    fontSize: '13px',
    lineHeight: '1.8'
  }
};

export default MemoryDemo;
