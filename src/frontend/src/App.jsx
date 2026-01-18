import React, { useState, useEffect } from 'react';
import { Wifi, Save, Activity, Volume2, Lightbulb, Power, Terminal, AlertTriangle, ChevronDown, ChevronRight, Usb, RefreshCw } from 'lucide-react';

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
    const interval = setInterval(fetchStatus, 500); // Faster poll for button feedback
    fetchStatus();
    return () => clearInterval(interval);
  }, []);

  const sendCommand = async (component, action) => {
    setLoading(true);
    setLastAction(`Sending ${action}...`);
    try {
      const res = await fetch(`/api/test/hardware/${component}?action=${action}`, { method: 'POST' });
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      const data = await res.json();
      setLastAction(`✅ Success: ${data.status}`);
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
          // Reload page after delay? Or just wait for reconnection
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
          <h1>Project Beatha</h1>
        </div>
        <div style={styles.badge(status.drone_connected ? 'success' : 'danger')}>
          <Wifi size={16} />
          <span>{status.drone_connected ? "Connected" : "Waiting for USB Connection"}</span>
        </div>
      </header>

      {/* Error Banner */}
      {status.error && (
        <div style={styles.errorBanner}>
          <AlertTriangle size={20} />
          <span>Backend Offline: {status.error}</span>
        </div>
      )}

      {/* Pin Config Card */}
      {hwConfig && (
        <CollapsibleCard title="⚙️ Hardware Configuration" defaultOpen={false}>
          <div style={styles.grid}>
            <ConfigInput label="LED Pin" name="led_pin" value={configForm.led_pin} onChange={handleConfigChange} />
            <ConfigInput label="Buzzer Pin" name="buzzer_pin" value={configForm.buzzer_pin} onChange={handleConfigChange} />
            <ConfigInput label="Dump Btn" name="button_dump_pin" value={configForm.button_dump_pin} onChange={handleConfigChange} />
            <ConfigInput label="Pair Btn" name="button_pair_pin" value={configForm.button_pair_pin} onChange={handleConfigChange} />
          </div>
          <div style={{ marginTop: '15px', textAlign: 'right' }}>
              <button style={styles.smBtn} onClick={saveConfig} disabled={loading}>
                  <RefreshCw size={16} className={loading ? "spin" : ""} /> Save & Restart Backend
              </button>
          </div>
        </CollapsibleCard>
      )}

      {/* USB Menu */}
      <CollapsibleCard title="🔌 USB Menu" icon={<Usb size={20} />} defaultOpen={false}>
        <div style={styles.emptyState}>
          <p>USB Device List (Coming Soon)</p>
        </div>
      </CollapsibleCard>

      {/* Hardware Test Card */}
      <CollapsibleCard title="🛠️ Hardware Test" defaultOpen={true}>
        <div style={styles.statusRow}>
            <StatusIndicator label="Dump Button" active={status.buttons?.dump} />
            <StatusIndicator label="Pair Button" active={status.buttons?.pair} />
        </div>
        <div style={styles.grid}>
          <ControlBtn icon={<Lightbulb />} label="Green LED" color="#2ecc71" onClick={() => sendCommand('led', 'green')} />
          <ControlBtn icon={<Lightbulb />} label="Red LED" color="#e74c3c" onClick={() => sendCommand('led', 'red')} />
          <ControlBtn icon={<Volume2 />} label="Beep (ESC)" color="#f1c40f" onClick={() => sendCommand('buzzer', 'on')} />
          <ControlBtn icon={<Power />} label="LED Off" color="#95a5a6" onClick={() => sendCommand('led', 'off')} />
        </div>
        <div style={styles.consoleLog}>
          <Terminal size={14} style={{ marginRight: '8px' }} />
          <span>{lastAction || "Ready"}</span>
        </div>
      </CollapsibleCard>

      {/* Dumps Card */}
      <div style={styles.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={styles.cardTitle}>📂 Firmware Dumps</h2>
          <button style={styles.smBtn} onClick={() => sendCommand('dump', 'start')}>
            <Save size={16} /> New Dump
          </button>
        </div>
        <div style={styles.emptyState}>
          <p>No dumps found on device.</p>
        </div>
      </div>

      {/* Footer */}
      <footer style={styles.footer}>
        v0.1 (Alpha) | Build: {new Date().toLocaleDateString()} {new Date().toLocaleTimeString()}
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

const styles = {
  container: { maxWidth: '600px', margin: '0 auto', padding: '20px' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' },
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
  card: { background: '#2d2d2d', borderRadius: '12px', padding: '20px', marginBottom: '20px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  cardTitle: { margin: '0 0 15px 0', fontSize: '18px', color: '#ecf0f1' },
  grid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' },
  statusRow: { display: 'flex', gap: '20px', marginBottom: '15px', padding: '10px', background: '#222', borderRadius: '8px' },
  btn: {
    display: 'flex', alignItems: 'center', gap: '10px', padding: '15px',
    background: '#3a3a3a', border: 'none', borderRadius: '8px',
    color: 'white', fontSize: '15px', cursor: 'pointer', textAlign: 'left'
  },
  smBtn: {
    display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 12px',
    background: '#3498db', border: 'none', borderRadius: '6px', color: 'white', cursor: 'pointer', fontSize: '14px'
  },
  consoleLog: {
    marginTop: '15px', padding: '10px', background: '#1a1a1a', borderRadius: '6px',
    color: '#bdc3c7', fontFamily: 'monospace', fontSize: '13px', display: 'flex', alignItems: 'center'
  },
  infoItem: { background: '#3a3a3a', padding: '10px', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  label: { color: '#bdc3c7', fontSize: '14px' },
  val: { color: '#fff', fontWeight: 'bold', fontSize: '14px' },
  input: { background: 'transparent', border: 'none', color: '#fff', textAlign: 'right', fontSize: '14px', fontWeight: 'bold', width: '100px' },
  emptyState: { padding: '20px', textAlign: 'center', color: '#7f8c8d', border: '1px dashed #444', borderRadius: '8px' },
  footer: { textAlign: 'center', marginTop: '40px', color: '#555', fontSize: '12px', borderTop: '1px solid #333', paddingTop: '20px' }
};

export default App;
