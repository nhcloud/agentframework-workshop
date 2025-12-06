import React from 'react';

/**
 * MemoryToggle - Reusable component for enabling/disabling agent memory
 * 
 * @param {Object} props
 * @param {boolean} props.enabled - Current memory state
 * @param {Function} props.onChange - Callback when toggle changes
 * @param {Object} props.stats - Optional stats to display {name, persona, messageCount}
 * @param {boolean} props.showStats - Whether to show memory stats
 * @param {string} props.size - Size variant: 'small', 'medium', 'large'
 */
const MemoryToggle = ({ 
  enabled = false, 
  onChange, 
  stats = null,
  showStats = true,
  size = 'medium'
}) => {
  const sizeStyles = {
    small: {
      switch: { width: '44px', height: '24px' },
      ball: { width: '18px', height: '18px', left: '3px', bottom: '3px' },
      ballActive: { transform: 'translateX(20px)' },
      icon: { fontSize: '18px' },
      text: { fontSize: '14px' }
    },
    medium: {
      switch: { width: '60px', height: '34px' },
      ball: { width: '26px', height: '26px', left: '4px', bottom: '4px' },
      ballActive: { transform: 'translateX(26px)' },
      icon: { fontSize: '24px' },
      text: { fontSize: '18px' }
    },
    large: {
      switch: { width: '76px', height: '44px' },
      ball: { width: '36px', height: '36px', left: '4px', bottom: '4px' },
      ballActive: { transform: 'translateX(32px)' },
      icon: { fontSize: '32px' },
      text: { fontSize: '22px' }
    }
  };

  const currentSize = sizeStyles[size];

  return (
    <div style={{
      ...styles.container,
      ...(enabled ? styles.containerActive : {})
    }}>
      <label style={styles.label}>
        {/* Toggle Switch */}
        <div style={{ ...styles.switch, ...currentSize.switch }}>
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => onChange(e.target.checked)}
            style={styles.input}
          />
          <span style={{
            ...styles.slider,
            ...(enabled ? styles.sliderActive : {})
          }}>
            <span style={{
              ...styles.ball,
              ...currentSize.ball,
              ...(enabled ? currentSize.ballActive : {})
            }}></span>
          </span>
        </div>

        {/* Status Display */}
        <div style={styles.status}>
          <span style={{ ...styles.icon, ...currentSize.icon }}>
            {enabled ? '??' : '??'}
          </span>
          <div style={styles.textGroup}>
            <span style={{ ...styles.text, ...currentSize.text }}>
              {enabled ? 'Memory Enabled' : 'Memory Disabled'}
            </span>
            <span style={styles.description}>
              {enabled 
                ? 'Agent remembers your info' 
                : 'Agent won\'t remember context'}
            </span>
          </div>
        </div>
      </label>

      {/* Memory Stats */}
      {enabled && showStats && stats && (
        <div style={styles.stats}>
          <div style={styles.statsHeader}>?? Memory Status</div>
          <div style={styles.statsGrid}>
            {stats.name && (
              <div style={styles.statItem}>
                <span style={styles.statIcon}>??</span>
                <div style={styles.statContent}>
                  <span style={styles.statLabel}>Name</span>
                  <span style={styles.statValue}>{stats.name}</span>
                </div>
              </div>
            )}
            {stats.persona && (
              <div style={styles.statItem}>
                <span style={styles.statIcon}>??</span>
                <div style={styles.statContent}>
                  <span style={styles.statLabel}>Persona</span>
                  <span style={styles.statValue}>{stats.persona}</span>
                </div>
              </div>
            )}
            {stats.messageCount !== undefined && (
              <div style={styles.statItem}>
                <span style={styles.statIcon}>??</span>
                <div style={styles.statContent}>
                  <span style={styles.statLabel}>Messages</span>
                  <span style={styles.statValue}>{stats.messageCount}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Help Text */}
      {enabled && (
        <div style={styles.helpText}>
          ?? Try saying "My name is..." or "I'm a..." to help the agent remember you
        </div>
      )}
    </div>
  );
};

const styles = {
  container: {
    backgroundColor: 'white',
    padding: '20px',
    borderRadius: '12px',
    border: '2px solid #e0e4e8',
    transition: 'all 0.3s ease',
    marginBottom: '16px'
  },
  containerActive: {
    background: 'linear-gradient(135deg, #e7f3ff 0%, #f0e7ff 100%)',
    borderColor: '#667eea',
    boxShadow: '0 4px 12px rgba(102, 126, 234, 0.2)'
  },
  label: {
    display: 'flex',
    alignItems: 'center',
    cursor: 'pointer',
    userSelect: 'none'
  },
  switch: {
    position: 'relative',
    display: 'inline-block',
    flexShrink: 0,
    marginRight: '15px'
  },
  input: {
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
  ball: {
    position: 'absolute',
    backgroundColor: 'white',
    borderRadius: '50%',
    transition: 'transform 0.4s',
    boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
  },
  status: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    flex: 1
  },
  icon: {
    lineHeight: 1
  },
  textGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px'
  },
  text: {
    fontWeight: '600',
    color: '#2c3e50',
    lineHeight: 1.2
  },
  description: {
    fontSize: '12px',
    color: '#6c757d',
    lineHeight: 1.2
  },
  stats: {
    marginTop: '16px',
    padding: '16px',
    background: 'rgba(255, 255, 255, 0.7)',
    borderRadius: '8px',
    border: '1px solid rgba(102, 126, 234, 0.2)'
  },
  statsHeader: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#495057',
    marginBottom: '12px'
  },
  statsGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px'
  },
  statItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '8px 12px',
    background: 'white',
    borderRadius: '6px',
    border: '1px solid #e9ecef'
  },
  statIcon: {
    fontSize: '20px',
    lineHeight: 1
  },
  statContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    flex: 1
  },
  statLabel: {
    fontSize: '11px',
    color: '#6c757d',
    textTransform: 'uppercase',
    fontWeight: '600',
    letterSpacing: '0.5px'
  },
  statValue: {
    fontSize: '14px',
    color: '#667eea',
    fontWeight: '600',
    fontFamily: '"Courier New", monospace'
  },
  helpText: {
    marginTop: '12px',
    padding: '10px 12px',
    background: '#fff3cd',
    border: '1px solid #ffc107',
    borderRadius: '6px',
    fontSize: '13px',
    color: '#856404',
    lineHeight: 1.4
  }
};

export default MemoryToggle;
