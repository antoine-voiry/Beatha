import React, { useState, useEffect } from 'react';
import { Wifi, Save, Activity, Volume2, Lightbulb, Power, Terminal, AlertTriangle, ChevronDown, ChevronRight, Usb, RefreshCw, Bluetooth, FileText } from 'lucide-react';

function App() {
  const [status, setStatus] = useState({ drone_connected: false, mode: 'OFFLINE', error: null, buttons: { dump: false, pair: false } });
  const [hwConfig, setHwConfig] = useState(null);
  const [configForm, setConfigForm] = useState({});
  const [lastAction, setLastAction] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/status');
        if (!res.ok) throw new Error(`Server Error: ${res.status}`);
        const data = await res.json();
        setStatus({ ...data, error: null });
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
    const interval = setInterval(fetchStatus, 1000);
    fetchStatus();
    return () => clearInterval(interval);
  }, []);

  const sendHardwareCommand = async (component, action) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/test/hardware/${component}?action=${action}`, { method: 'POST' });
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      const data = await res.json();
      setLastAction(`✅ Hardware: ${data.status}`);
    } catch (e) {
      setLastAction(`❌ Error: ${e.message}`);
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
          setLastAction(`✅ ${data.status}`);
      } catch (e) {
          setLastAction(`❌ Error: ${e.message}`);
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
          setLastAction(`✅ ${data.status}`);
          setTimeout(() => window.location.reload(), 3000);
      } catch (e) {
          setLastAction(`❌ Error: ${e.message}`);
      } finally {
          setLoading(false);
      }
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.logo}>
          <img src="/logo.png" alt="Logo" height="40" style={{ borderRadius: '5px' }} />
          <div>
            <h1 style={{ margin: 0, fontSize: '1.2rem' }}>Project Beatha</h1>
            <span style={{ fontSize: '0.8rem', color: '#7f8c8d' }}>FPV Recovery Tool</span>
          </div>
        </div>
        <div style={styles.badge(status.drone_connected ? 'success' : 'danger')}>
          <Usb size={16} />
          <span style={{ display: 'none', '@media (min-width: 400px)': { display: 'inline' } }}>
             {status.drone_connected ? "Connected" : "No USB"}
          </span>
        </div>
      </header>

      {/* Error Banner */}
      {status.error && (
        <div style={styles.errorBanner}>
          <AlertTriangle size={20} />
          <span>Backend Offline: {status.error}</span>
        </div>
      )}

      {/* Main Status Card */}
      <div style={styles.card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <h2 style={styles.cardTitle}>Status: {status.mode}</h2>
              {status.mode !== 'IDLE' && <Activity className="spin" color="#3498db" />}
          </div>

          {status.serial_port && (
            <div style={{ marginBottom: '15px', padding: '10px', background: '#1a1a1a', borderRadius: '6px', fontSize: '14px' }}>
              <div style={{ color: '#7f8c8d', marginBottom: '5px' }}>Serial Config:</div>
              <div style={{ color: '#ecf0f1', fontFamily: 'monospace' }}>
                {status.serial_port} @ {status.baud_rate} baud
              </div>
            </div>
          )}

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

      {/* Latest Dump Info */}
      {status.latest_dump && (
        <CollapsibleCard title="📊 Latest Dump" defaultOpen={true}>
          <DumpInfo dump={status.latest_dump} />
        </CollapsibleCard>
      )}

      {/* Hardware Configuration */}
      {hwConfig && (
        <CollapsibleCard title="⚙️ Hardware Config" defaultOpen={false}>
          <div style={styles.grid}>
            <ConfigInput label="LED Pin" name="led_pin" value={configForm.led_pin} onChange={handleConfigChange} />
            <ConfigInput label="Buzzer Pin" name="buzzer_pin" value={configForm.buzzer_pin} onChange={handleConfigChange} />
            <ConfigInput label="Dump Btn" name="button_dump_pin" value={configForm.button_dump_pin} onChange={handleConfigChange} />
            <ConfigInput label="Pair Btn" name="button_pair_pin" value={configForm.button_pair_pin} onChange={handleConfigChange} />
          </div>
          <div style={{ marginTop: '15px', textAlign: 'right' }}>
              <button style={styles.smBtn} onClick={saveConfig} disabled={loading}>
                  <RefreshCw size={16} className={loading ? "spin" : ""} /> Save & Restart
              </button>
          </div>
        </CollapsibleCard>
      )}

      {/* Hardware Test Card */}
      <CollapsibleCard title="🛠️ Hardware Test" defaultOpen={false}>
        <div style={styles.statusRow}>
            <StatusIndicator label="Dump Button" active={status.buttons?.dump} />
            <StatusIndicator label="Pair Button" active={status.buttons?.pair} />
        </div>
        <div style={styles.grid}>
          <ControlBtn icon={<Lightbulb />} label="Green" color="#2ecc71" onClick={() => sendHardwareCommand('led', 'green')} />
          <ControlBtn icon={<Lightbulb />} label="Red" color="#e74c3c" onClick={() => sendHardwareCommand('led', 'red')} />
          <ControlBtn icon={<Volume2 />} label="Beep" color="#f1c40f" onClick={() => sendHardwareCommand('buzzer', 'on')} />
          <ControlBtn icon={<Power />} label="Off" color="#95a5a6" onClick={() => sendHardwareCommand('led', 'off')} />
        </div>
        <div style={styles.consoleLog}>
          <Terminal size={18} style={{ marginRight: '10px', flexShrink: 0 }} />
          <span style={{ wordBreak: 'break-word', flex: 1 }}>{lastAction || "Ready"}</span>
        </div>
      </CollapsibleCard>

      {/* Footer */}
      <footer style={styles.footer}>
        v0.1.0-alpha | {new Date().toLocaleDateString()}
      </footer>
    </div>
  );
}

// Components
const CollapsibleCard = ({ title, icon, children, defaultOpen = true }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  return (
    <div style={styles.card}>
      <div
        style={{ ...styles.cardHeader, cursor: 'pointer' }}
        onClick={() => setIsOpen(!isOpen)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {icon}
          <h2 style={{ ...styles.cardTitle, margin: 0 }}>{title}</h2>
        </div>
        {isOpen ? <ChevronDown size={20} color="#7f8c8d" /> : <ChevronRight size={20} color="#7f8c8d" />}
      </div>
      {isOpen && <div style={{ marginTop: '15px' }}>{children}</div>}
    </div>
  );
};

const ConfigInput = ({ label, name, value, onChange }) => (
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

const StatusIndicator = ({ label, active }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
        <div style={{
            width: '12px', height: '12px', borderRadius: '50%',
            background: active ? '#2ecc71' : '#3a3a3a',
            border: active ? '2px solid #27ae60' : '2px solid #555'
        }} />
        <span style={{ color: active ? '#fff' : '#7f8c8d', fontSize: '14px' }}>{label}</span>
    </div>
);

const ControlBtn = ({ icon, label, color, onClick }) => (
  <button onClick={onClick} style={{ ...styles.btn, borderLeft: `4px solid ${color}` }}>
    <div style={{ color }}>{icon}</div>
    <span>{label}</span>
  </button>
);

const DumpInfo = ({ dump }) => {
  const [dumpData, setDumpData] = useState(null);
  const [loading, setLoading] = useState(false);

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
        <div style={{ marginTop: '15px', textAlign: 'center', color: '#7f8c8d' }}>
          <Activity className="spin" size={20} style={{ display: 'inline-block' }} />
          <span style={{ marginLeft: '8px' }}>Loading dump content...</span>
        </div>
      )}

      {dumpData && (
        <div style={{ marginTop: '15px' }}>
          {dumpData.version && (
            <div style={{ ...styles.infoItem, marginBottom: '10px', background: '#1a472a', borderLeft: '4px solid #2ecc71' }}>
              <span style={styles.label}>Version:</span>
              <span style={{ ...styles.val, color: '#2ecc71' }}>{dumpData.version}</span>
            </div>
          )}
          <details style={{ marginTop: '10px' }}>
            <summary style={{ cursor: 'pointer', color: '#3498db', padding: '10px', background: '#1a1a1a', borderRadius: '6px' }}>
              View Full Dump ({dumpData.content.split('\n').length} lines)
            </summary>
            <pre style={{
              marginTop: '10px',
              padding: '15px',
              background: '#1a1a1a',
              borderRadius: '6px',
              color: '#bdc3c7',
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

const styles = {
  container: { width: '100%', maxWidth: '800px', margin: '0 auto', padding: '10px', boxSizing: 'border-box' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' },
  logo: { display: 'flex', alignItems: 'center', gap: '10px' },
  badge: (type) => ({
    display: 'flex', alignItems: 'center', gap: '6px',
    padding: '6px 12px', borderRadius: '20px',
    background: type === 'success' ? 'rgba(46, 204, 113, 0.2)' : 'rgba(231, 76, 60, 0.2)',
    color: type === 'success' ? '#2ecc71' : '#e74c3c',
    fontSize: '14px', fontWeight: 'bold'
  }),
  errorBanner: {
    background: '#e74c3c', color: 'white', padding: '12px', borderRadius: '8px',
    display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px'
  },
  card: { background: '#2d2d2d', borderRadius: '12px', padding: '15px', marginBottom: '15px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  cardTitle: { margin: '0 0 5px 0', fontSize: '18px', color: '#ecf0f1' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px' },
  statusRow: { display: 'flex', gap: '20px', marginBottom: '15px', padding: '10px', background: '#222', borderRadius: '8px' },
  btn: {
    display: 'flex', alignItems: 'center', gap: '10px', padding: '15px',
    background: '#3a3a3a', border: 'none', borderRadius: '8px',
    color: 'white', fontSize: '15px', cursor: 'pointer', textAlign: 'left', width: '100%'
  },
  actionBtn: (active) => ({
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '10px',
      padding: '20px', borderRadius: '10px', border: 'none',
      background: active ? '#2980b9' : '#34495e',
      color: active ? 'white' : '#7f8c8d',
      cursor: active ? 'pointer' : 'not-allowed',
      fontWeight: 'bold', fontSize: '16px',
      opacity: active ? 1 : 0.7
  }),
  smBtn: {
    display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 12px',
    background: '#3498db', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontSize: '14px'
  },
  consoleLog: {
    marginTop: '15px', padding: '20px', background: '#1a1a1a', borderRadius: '8px',
    color: '#ecf0f1', fontFamily: 'monospace', fontSize: '16px',
    display: 'flex', alignItems: 'flex-start',
    minHeight: '80px', lineHeight: '1.6',
    border: '1px solid #2c3e50'
  },
  infoItem: { background: '#3a3a3a', padding: '10px', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  label: { color: '#bdc3c7', fontSize: '14px' },
  val: { color: '#fff', fontWeight: 'bold', fontSize: '14px' },
  input: { background: 'transparent', border: 'none', color: '#fff', textAlign: 'right', fontSize: '14px', fontWeight: 'bold', width: '80px' },
  footer: { textAlign: 'center', marginTop: '20px', color: '#555', fontSize: '12px', borderTop: '1px solid #333', paddingTop: '20px' }
};

export default App;
