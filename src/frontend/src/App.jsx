import React, { useState, useEffect, useCallback, createContext, useContext } from 'react';
import {
  Wifi, Save, Activity, Volume2, Lightbulb, Power, Terminal, AlertTriangle,
  ChevronDown, ChevronRight, Usb, RefreshCw, Bluetooth, FileText,
  Sun, Moon, Settings, Cpu, Cable, Check, X, PlugZap, Unplug
} from 'lucide-react';

// Theme Context
const ThemeContext = createContext();

const useTheme = () => useContext(ThemeContext);

const ThemeProvider = ({ children }) => {
  const [isDark, setIsDark] = useState(() => {
    const saved = localStorage.getItem('theme');
    return saved ? saved === 'dark' : true; // Default to dark
  });

  useEffect(() => {
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    document.body.style.backgroundColor = isDark ? '#1a1a1a' : '#f5f5f5';
    document.body.style.color = isDark ? '#ffffff' : '#1a1a1a';
  }, [isDark]);

  const toggleTheme = () => setIsDark(!isDark);

  const theme = isDark ? {
    bg: '#1a1a1a',
    cardBg: '#2d2d2d',
    cardBgAlt: '#3a3a3a',
    text: '#ffffff',
    textMuted: '#7f8c8d',
    accent: '#3498db',
    success: '#2ecc71',
    danger: '#e74c3c',
    warning: '#f1c40f',
    border: '#444',
    inputBg: '#1a1a1a',
  } : {
    bg: '#f5f5f5',
    cardBg: '#ffffff',
    cardBgAlt: '#f0f0f0',
    text: '#1a1a1a',
    textMuted: '#666',
    accent: '#2980b9',
    success: '#27ae60',
    danger: '#c0392b',
    warning: '#f39c12',
    border: '#ddd',
    inputBg: '#ffffff',
  };

  return (
    <ThemeContext.Provider value={{ theme, isDark, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}

function AppContent() {
  const { theme, isDark, toggleTheme } = useTheme();
  const [activeTab, setActiveTab] = useState('main'); // 'main' or 'preferences'
  const [status, setStatus] = useState({
    drone_connected: false,
    mode: 'OFFLINE',
    error: null,
    buttons: { dump: false, pair: false },
    fc_info: null
  });
  const [hwConfig, setHwConfig] = useState(null);
  const [configForm, setConfigForm] = useState({});
  const [lastAction, setLastAction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [serialPorts, setSerialPorts] = useState([]);
  const [selectedPort, setSelectedPort] = useState('');
  const [selectedBaud, setSelectedBaud] = useState(115200);
  const [fcLogs, setFcLogs] = useState([]);
  const [connecting, setConnecting] = useState(false);
  const [refreshingPorts, setRefreshingPorts] = useState(false);

  const baudRates = [9600, 19200, 38400, 57600, 115200, 230400, 250000, 400000, 500000, 921600];

  // Fetch status periodically
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/status');
        if (!res.ok) throw new Error(`Server Error: ${res.status}`);
        const data = await res.json();
        setStatus({ ...data, error: null });
        if (data.serial_port) {
          setSelectedPort(data.serial_port);
        }
        if (data.baud_rate) {
          setSelectedBaud(data.baud_rate);
        }
      } catch (e) {
        setStatus(prev => ({ ...prev, drone_connected: false, mode: 'OFFLINE', error: e.message }));
      }
    };

    const fetchConfig = async () => {
      try {
        const res = await fetch('/api/config');
        if (res.ok) {
          const data = await res.json();
          setHwConfig(data);
          setConfigForm(data);
        }
      } catch (e) { console.error("Config fetch failed", e); }
    };

    fetchConfig();
    fetchSerialPorts();
    const interval = setInterval(fetchStatus, 1000);
    fetchStatus();
    return () => clearInterval(interval);
  }, []);

  // Fetch logs periodically when on main tab
  useEffect(() => {
    if (activeTab !== 'main') return;

    const fetchLogs = async () => {
      try {
        const res = await fetch('/api/logs');
        if (res.ok) {
          const data = await res.json();
          setFcLogs(data.logs || []);
        }
      } catch (e) { /* ignore */ }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 1000);
    return () => clearInterval(interval);
  }, [activeTab]);

  const fetchSerialPorts = async () => {
    setRefreshingPorts(true);
    try {
      const res = await fetch('/api/serial/ports');
      if (res.ok) {
        const data = await res.json();
        setSerialPorts(data.ports || []);
      }
    } catch (e) { console.error("Failed to fetch ports", e); }
    finally { setRefreshingPorts(false); }
  };

  const connectSerial = async () => {
    if (!selectedPort) return;
    setConnecting(true);
    try {
      const res = await fetch('/api/serial/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ port: selectedPort, baud_rate: selectedBaud })
      });
      if (res.ok) {
        const data = await res.json();
        setLastAction(`Connected to ${selectedPort}`);
      } else {
        throw new Error('Connection failed');
      }
    } catch (e) {
      setLastAction(`Connection error: ${e.message}`);
    } finally {
      setConnecting(false);
    }
  };

  const disconnectSerial = async () => {
    try {
      await fetch('/api/serial/disconnect', { method: 'POST' });
      setLastAction('Disconnected');
    } catch (e) {
      setLastAction(`Disconnect error: ${e.message}`);
    }
  };

  const sendHardwareCommand = async (component, action) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/test/hardware/${component}?action=${action}`, { method: 'POST' });
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      const data = await res.json();
      setLastAction(`Hardware: ${data.status}`);
    } catch (e) {
      setLastAction(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const triggerAction = async (actionName) => {
    setLoading(true);
    setLastAction(`Requesting ${actionName}...`);
    try {
      const res = await fetch(`/api/action/${actionName}`, { method: 'POST' });
      if (!res.ok) throw new Error("Action Failed");
      const data = await res.json();
      setLastAction(data.status);
    } catch (e) {
      setLastAction(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleConfigChange = (e) => {
    const { name, value } = e.target;
    setConfigForm(prev => ({ ...prev, [name]: parseInt(value) || value }));
  };

  const saveConfig = async () => {
    setLoading(true);
    setLastAction("Saving Config & Restarting...");
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(configForm)
      });
      if (!res.ok) throw new Error("Save Failed");
      const data = await res.json();
      setLastAction(data.status);
      setTimeout(() => window.location.reload(), 3000);
    } catch (e) {
      setLastAction(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const styles = createStyles(theme);

  return (
    <div style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.logo}>
          <img src="/logo.png" alt="Logo" height="40" style={{ borderRadius: '5px' }} />
          <div>
            <h1 style={{ margin: 0, fontSize: '1.2rem', color: theme.text }}>Project Beatha</h1>
            <span style={{ fontSize: '0.8rem', color: theme.textMuted }}>FPV Recovery Tool</span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button onClick={toggleTheme} style={styles.iconBtn} title="Toggle theme">
            {isDark ? <Sun size={20} /> : <Moon size={20} />}
          </button>
          <div style={styles.badge(status.drone_connected ? 'success' : 'danger')}>
            <Usb size={16} />
            <span>{status.drone_connected ? "Connected" : "No USB"}</span>
          </div>
        </div>
      </header>

      {/* Error Banner */}
      {status.error && (
        <div style={styles.errorBanner}>
          <AlertTriangle size={20} />
          <span>Backend Offline: {status.error}</span>
        </div>
      )}

      {/* Tab Navigation */}
      <div style={styles.tabNav}>
        <button
          style={styles.tab(activeTab === 'main')}
          onClick={() => setActiveTab('main')}
        >
          <Cpu size={18} />
          <span>Flight Controller</span>
        </button>
        <button
          style={styles.tab(activeTab === 'preferences')}
          onClick={() => setActiveTab('preferences')}
        >
          <Settings size={18} />
          <span>Preferences</span>
        </button>
      </div>

      {/* Main Tab */}
      {activeTab === 'main' && (
        <>
          {/* Status Card */}
          <div style={styles.card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
              <h2 style={styles.cardTitle}>Status: {status.mode}</h2>
              {status.mode !== 'IDLE' && status.mode !== 'OFFLINE' && <Activity className="spin" color={theme.accent} />}
            </div>

            {/* Connection Panel */}
            <div style={styles.connectionPanel}>
              <div style={styles.connectionRow}>
                <div style={{ flex: 1 }}>
                  <label style={styles.label}>Serial Port</label>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <select
                      value={selectedPort}
                      onChange={(e) => setSelectedPort(e.target.value)}
                      style={styles.select}
                      disabled={refreshingPorts}
                    >
                      {refreshingPorts ? (
                        <option value="">Scanning...</option>
                      ) : serialPorts.length === 0 ? (
                        <option value="">No ports found</option>
                      ) : (
                        <>
                          <option value="">Select port...</option>
                          {serialPorts.map(p => (
                            <option key={p.device} value={p.device}>
                              {p.device} - {p.description} {p.is_current ? '(current)' : ''}
                            </option>
                          ))}
                        </>
                      )}
                    </select>
                    <button
                      onClick={fetchSerialPorts}
                      style={styles.iconBtn}
                      title="Refresh USB ports"
                      disabled={refreshingPorts}
                    >
                      <RefreshCw size={16} className={refreshingPorts ? 'spin' : ''} />
                    </button>
                  </div>
                </div>
                <div style={{ width: '120px' }}>
                  <label style={styles.label}>Baud Rate</label>
                  <select
                    value={selectedBaud}
                    onChange={(e) => setSelectedBaud(parseInt(e.target.value))}
                    style={styles.select}
                  >
                    {baudRates.map(b => (
                      <option key={b} value={b}>{b}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                <button
                  onClick={connectSerial}
                  disabled={!selectedPort || connecting || status.drone_connected}
                  style={styles.connectBtn(true)}
                >
                  <PlugZap size={18} />
                  <span>{connecting ? 'Connecting...' : 'Connect'}</span>
                </button>
                <button
                  onClick={disconnectSerial}
                  disabled={!status.drone_connected}
                  style={styles.connectBtn(false)}
                >
                  <Unplug size={18} />
                  <span>Disconnect</span>
                </button>
              </div>
            </div>

            {/* FC Info */}
            {status.fc_info && (
              <div style={styles.fcInfo}>
                <div style={styles.fcInfoRow}>
                  <span style={styles.fcInfoLabel}>Type:</span>
                  <span style={styles.fcInfoValue}>{status.fc_info.type}</span>
                </div>
                <div style={styles.fcInfoRow}>
                  <span style={styles.fcInfoLabel}>Version:</span>
                  <span style={styles.fcInfoValue}>{status.fc_info.version}</span>
                </div>
                {status.fc_info.target && status.fc_info.target !== 'Unknown' && (
                  <div style={styles.fcInfoRow}>
                    <span style={styles.fcInfoLabel}>Target:</span>
                    <span style={styles.fcInfoValue}>{status.fc_info.target}</span>
                  </div>
                )}
              </div>
            )}

            {/* Action Buttons */}
            <div style={styles.grid}>
              <button
                style={styles.actionBtn(status.mode === 'IDLE' && status.drone_connected)}
                disabled={status.mode !== 'IDLE' || !status.drone_connected}
                onClick={() => triggerAction('dump')}
              >
                <Save size={24} />
                <span>Start Dump</span>
              </button>

              <button
                style={styles.actionBtn(status.mode === 'IDLE')}
                disabled={status.mode !== 'IDLE'}
                onClick={() => triggerAction('pair')}
              >
                <Bluetooth size={24} />
                <span>Start Pairing</span>
              </button>
            </div>
          </div>

          {/* Logs Card */}
          <div style={styles.card}>
            <h2 style={styles.cardTitle}>FC Communication Log</h2>
            <div style={styles.logContainer}>
              {fcLogs.length === 0 ? (
                <div style={styles.logEmpty}>No logs yet. Connect to FC and perform an action.</div>
              ) : (
                fcLogs.map((log, i) => (
                  <div key={i} style={styles.logEntry(log.type)}>
                    <span style={styles.logTime}>{new Date(log.timestamp).toLocaleTimeString()}</span>
                    <span style={styles.logType(log.type)}>{log.type.toUpperCase()}</span>
                    <span style={styles.logMsg}>{log.message}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Latest Dump Info */}
          {status.latest_dump && (
            <CollapsibleCard title="Latest Dump" icon={<FileText size={18} />} defaultOpen={false} theme={theme}>
              <DumpInfo dump={status.latest_dump} theme={theme} />
            </CollapsibleCard>
          )}
        </>
      )}

      {/* Preferences Tab */}
      {activeTab === 'preferences' && (
        <>
          {/* Hardware Configuration */}
          {hwConfig && (
            <CollapsibleCard title="Hardware Configuration" icon={<Cable size={18} />} defaultOpen={true} theme={theme}>
              <div style={styles.grid}>
                <ConfigInput label="LED Pin" name="led_pin" value={configForm.led_pin} onChange={handleConfigChange} theme={theme} />
                <ConfigInput label="Buzzer Pin" name="buzzer_pin" value={configForm.buzzer_pin} onChange={handleConfigChange} theme={theme} />
                <ConfigInput label="Dump Btn Pin" name="button_dump_pin" value={configForm.button_dump_pin} onChange={handleConfigChange} theme={theme} />
                <ConfigInput label="Pair Btn Pin" name="button_pair_pin" value={configForm.button_pair_pin} onChange={handleConfigChange} theme={theme} />
              </div>
              <div style={{ marginTop: '15px', textAlign: 'right' }}>
                <button style={styles.smBtn} onClick={saveConfig} disabled={loading}>
                  <RefreshCw size={16} className={loading ? "spin" : ""} /> Save & Restart
                </button>
              </div>
            </CollapsibleCard>
          )}

          {/* Hardware Test Card */}
          <CollapsibleCard title="Hardware Test" icon={<Lightbulb size={18} />} defaultOpen={true} theme={theme}>
            <div style={styles.statusRow}>
              <StatusIndicator label="Dump Button" active={status.buttons?.dump} theme={theme} />
              <StatusIndicator label="Pair Button" active={status.buttons?.pair} theme={theme} />
            </div>
            <div style={styles.grid}>
              <ControlBtn icon={<Lightbulb />} label="Green" color={theme.success} onClick={() => sendHardwareCommand('led', 'green')} theme={theme} />
              <ControlBtn icon={<Lightbulb />} label="Red" color={theme.danger} onClick={() => sendHardwareCommand('led', 'red')} theme={theme} />
              <ControlBtn icon={<Volume2 />} label="Beep" color={theme.warning} onClick={() => sendHardwareCommand('buzzer', 'on')} theme={theme} />
              <ControlBtn icon={<Power />} label="Off" color={theme.textMuted} onClick={() => sendHardwareCommand('led', 'off')} theme={theme} />
            </div>
            <div style={styles.consoleLog}>
              <Terminal size={18} style={{ marginRight: '10px', flexShrink: 0 }} />
              <span style={{ wordBreak: 'break-word', flex: 1 }}>{lastAction || "Ready"}</span>
            </div>
          </CollapsibleCard>

          {/* User Preferences */}
          <CollapsibleCard title="User Preferences" icon={<Settings size={18} />} defaultOpen={false} theme={theme}>
            <div style={styles.prefRow}>
              <span style={{ color: theme.text }}>Theme</span>
              <button onClick={toggleTheme} style={styles.prefBtn}>
                {isDark ? <><Moon size={16} /> Dark</> : <><Sun size={16} /> Light</>}
              </button>
            </div>
            <div style={styles.prefRow}>
              <span style={{ color: theme.text }}>Emulation Mode</span>
              <span style={{ color: status.emulation ? theme.warning : theme.success }}>
                {status.emulation ? 'Enabled' : 'Disabled'}
              </span>
            </div>
          </CollapsibleCard>
        </>
      )}

      {/* Footer */}
      <footer style={styles.footer}>
        v0.2.0-alpha | {new Date().toLocaleDateString()}
      </footer>
    </div>
  );
}

// Components
const CollapsibleCard = ({ title, icon, children, defaultOpen = true, theme }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const styles = createStyles(theme);

  return (
    <div style={styles.card}>
      <div
        style={{ ...styles.cardHeader, cursor: 'pointer' }}
        onClick={() => setIsOpen(!isOpen)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: theme.text }}>
          {icon}
          <h2 style={{ ...styles.cardTitle, margin: 0 }}>{title}</h2>
        </div>
        {isOpen ? <ChevronDown size={20} color={theme.textMuted} /> : <ChevronRight size={20} color={theme.textMuted} />}
      </div>
      {isOpen && <div style={{ marginTop: '15px' }}>{children}</div>}
    </div>
  );
};

const ConfigInput = ({ label, name, value, onChange, theme }) => {
  const styles = createStyles(theme);
  return (
    <div style={styles.infoItem}>
      <span style={styles.label}>{label}:</span>
      <input
        type="text"
        name={name}
        value={value || ''}
        onChange={onChange}
        style={styles.input}
      />
    </div>
  );
};

const StatusIndicator = ({ label, active, theme }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
    <div style={{
      width: '12px', height: '12px', borderRadius: '50%',
      background: active ? theme.success : theme.cardBgAlt,
      border: active ? `2px solid ${theme.success}` : `2px solid ${theme.border}`
    }} />
    <span style={{ color: active ? theme.text : theme.textMuted, fontSize: '14px' }}>{label}</span>
  </div>
);

const ControlBtn = ({ icon, label, color, onClick, theme }) => {
  const styles = createStyles(theme);
  return (
    <button onClick={onClick} style={{ ...styles.btn, borderLeft: `4px solid ${color}` }}>
      <div style={{ color }}>{icon}</div>
      <span style={{ color: theme.text }}>{label}</span>
    </button>
  );
};

const DumpInfo = ({ dump, theme }) => {
  const [dumpData, setDumpData] = useState(null);
  const [loading, setLoading] = useState(false);
  const styles = createStyles(theme);

  useEffect(() => {
    const fetchDumpContent = async () => {
      if (!dump?.filename) return;
      setLoading(true);
      try {
        const res = await fetch(`/api/dumps/${dump.filename}`);
        if (res.ok) {
          const data = await res.json();
          setDumpData(data);
        }
      } catch (e) {
        console.error("Failed to fetch dump content", e);
      } finally {
        setLoading(false);
      }
    };
    fetchDumpContent();
  }, [dump?.filename]);

  const formatTimestamp = (ts) => {
    if (!ts) return 'Unknown';
    const date = new Date(ts * 1000);
    return date.toLocaleString();
  };

  const formatSize = (bytes) => {
    if (!bytes) return '0 B';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div>
      <div style={styles.grid}>
        <div style={styles.infoItem}>
          <span style={styles.label}>Filename:</span>
          <span style={styles.val}>{dump.filename}</span>
        </div>
        <div style={styles.infoItem}>
          <span style={styles.label}>Size:</span>
          <span style={styles.val}>{formatSize(dump.size)}</span>
        </div>
        <div style={styles.infoItem}>
          <span style={styles.label}>Timestamp:</span>
          <span style={styles.val}>{formatTimestamp(dump.timestamp)}</span>
        </div>
      </div>

      {loading && (
        <div style={{ marginTop: '15px', textAlign: 'center', color: theme.textMuted }}>
          <Activity className="spin" size={20} style={{ display: 'inline-block' }} />
          <span style={{ marginLeft: '8px' }}>Loading dump content...</span>
        </div>
      )}

      {dumpData && (
        <div style={{ marginTop: '15px' }}>
          {dumpData.version && (
            <div style={{ ...styles.infoItem, marginBottom: '10px', background: theme.success + '22', borderLeft: `4px solid ${theme.success}` }}>
              <span style={styles.label}>Version:</span>
              <span style={{ ...styles.val, color: theme.success }}>{dumpData.version}</span>
            </div>
          )}
          <details style={{ marginTop: '10px' }}>
            <summary style={{ cursor: 'pointer', color: theme.accent, padding: '10px', background: theme.inputBg, borderRadius: '6px' }}>
              View Full Dump ({dumpData.content.split('\n').length} lines)
            </summary>
            <pre style={{
              marginTop: '10px',
              padding: '15px',
              background: theme.inputBg,
              borderRadius: '6px',
              color: theme.textMuted,
              fontFamily: 'monospace',
              fontSize: '12px',
              overflow: 'auto',
              maxHeight: '400px',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all'
            }}>
              {dumpData.content}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
};

// Styles factory
const createStyles = (theme) => ({
  container: {
    width: '100%',
    maxWidth: '800px',
    margin: '0 auto',
    padding: '10px',
    boxSizing: 'border-box',
    minHeight: '100vh'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '15px'
  },
  logo: { display: 'flex', alignItems: 'center', gap: '10px' },
  badge: (type) => ({
    display: 'flex', alignItems: 'center', gap: '6px',
    padding: '6px 12px', borderRadius: '20px',
    background: type === 'success' ? theme.success + '33' : theme.danger + '33',
    color: type === 'success' ? theme.success : theme.danger,
    fontSize: '14px', fontWeight: 'bold'
  }),
  iconBtn: {
    background: 'transparent',
    border: `1px solid ${theme.border}`,
    borderRadius: '8px',
    padding: '8px',
    cursor: 'pointer',
    color: theme.text,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  errorBanner: {
    background: theme.danger, color: 'white', padding: '12px', borderRadius: '8px',
    display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px'
  },
  tabNav: {
    display: 'flex',
    gap: '5px',
    marginBottom: '15px',
    background: theme.cardBg,
    padding: '5px',
    borderRadius: '10px'
  },
  tab: (active) => ({
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    padding: '12px',
    border: 'none',
    borderRadius: '8px',
    background: active ? theme.accent : 'transparent',
    color: active ? 'white' : theme.textMuted,
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: active ? 'bold' : 'normal',
    transition: 'all 0.2s'
  }),
  card: {
    background: theme.cardBg,
    borderRadius: '12px',
    padding: '15px',
    marginBottom: '15px',
    boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
  },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  cardTitle: { margin: '0 0 5px 0', fontSize: '18px', color: theme.text },
  connectionPanel: {
    background: theme.cardBgAlt,
    borderRadius: '8px',
    padding: '15px',
    marginBottom: '15px'
  },
  connectionRow: {
    display: 'flex',
    gap: '15px',
    alignItems: 'flex-end'
  },
  select: {
    width: '100%',
    padding: '10px',
    borderRadius: '6px',
    border: `1px solid ${theme.border}`,
    background: theme.inputBg,
    color: theme.text,
    fontSize: '14px'
  },
  connectBtn: (isConnect) => ({
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    padding: '12px',
    borderRadius: '8px',
    border: 'none',
    background: isConnect ? theme.success : theme.danger,
    color: 'white',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 'bold'
  }),
  fcInfo: {
    background: theme.cardBgAlt,
    borderRadius: '8px',
    padding: '15px',
    marginBottom: '15px',
    borderLeft: `4px solid ${theme.accent}`
  },
  fcInfoRow: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '5px'
  },
  fcInfoLabel: {
    color: theme.textMuted,
    fontSize: '14px'
  },
  fcInfoValue: {
    color: theme.text,
    fontWeight: 'bold',
    fontSize: '14px'
  },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px' },
  statusRow: { display: 'flex', gap: '20px', marginBottom: '15px', padding: '10px', background: theme.cardBgAlt, borderRadius: '8px' },
  btn: {
    display: 'flex', alignItems: 'center', gap: '10px', padding: '15px',
    background: theme.cardBgAlt, border: 'none', borderRadius: '8px',
    color: theme.text, fontSize: '15px', cursor: 'pointer', textAlign: 'left', width: '100%'
  },
  actionBtn: (active) => ({
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '10px',
    padding: '20px', borderRadius: '10px', border: 'none',
    background: active ? theme.accent : theme.cardBgAlt,
    color: active ? 'white' : theme.textMuted,
    cursor: active ? 'pointer' : 'not-allowed',
    fontWeight: 'bold', fontSize: '16px',
    opacity: active ? 1 : 0.7
  }),
  smBtn: {
    display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 12px',
    background: theme.accent, border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontSize: '14px'
  },
  consoleLog: {
    marginTop: '15px', padding: '20px', background: theme.inputBg, borderRadius: '8px',
    color: theme.text, fontFamily: 'monospace', fontSize: '16px',
    display: 'flex', alignItems: 'flex-start',
    minHeight: '60px', lineHeight: '1.6',
    border: `1px solid ${theme.border}`
  },
  logContainer: {
    maxHeight: '300px',
    overflowY: 'auto',
    background: theme.inputBg,
    borderRadius: '8px',
    padding: '10px',
    fontFamily: 'monospace',
    fontSize: '12px'
  },
  logEmpty: {
    color: theme.textMuted,
    textAlign: 'center',
    padding: '20px'
  },
  logEntry: (type) => ({
    display: 'flex',
    gap: '10px',
    padding: '4px 0',
    borderBottom: `1px solid ${theme.border}`,
    alignItems: 'flex-start'
  }),
  logTime: {
    color: theme.textMuted,
    fontSize: '11px',
    flexShrink: 0
  },
  logType: (type) => ({
    padding: '2px 6px',
    borderRadius: '4px',
    fontSize: '10px',
    fontWeight: 'bold',
    flexShrink: 0,
    background: type === 'tx' ? theme.accent + '33' :
                type === 'rx' ? theme.success + '33' :
                type === 'error' ? theme.danger + '33' : theme.cardBgAlt,
    color: type === 'tx' ? theme.accent :
           type === 'rx' ? theme.success :
           type === 'error' ? theme.danger : theme.textMuted
  }),
  logMsg: {
    color: theme.text,
    wordBreak: 'break-all',
    flex: 1
  },
  infoItem: {
    background: theme.cardBgAlt,
    padding: '10px',
    borderRadius: '6px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  label: { color: theme.textMuted, fontSize: '14px' },
  val: { color: theme.text, fontWeight: 'bold', fontSize: '14px' },
  input: {
    background: 'transparent',
    border: 'none',
    color: theme.text,
    textAlign: 'right',
    fontSize: '14px',
    fontWeight: 'bold',
    width: '80px'
  },
  prefRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px',
    background: theme.cardBgAlt,
    borderRadius: '8px',
    marginBottom: '10px'
  },
  prefBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 12px',
    border: `1px solid ${theme.border}`,
    borderRadius: '6px',
    background: 'transparent',
    color: theme.text,
    cursor: 'pointer'
  },
  footer: {
    textAlign: 'center',
    marginTop: '20px',
    color: theme.textMuted,
    fontSize: '12px',
    borderTop: `1px solid ${theme.border}`,
    paddingTop: '20px'
  }
});

export default App;
