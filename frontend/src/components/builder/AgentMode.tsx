import React, { useState, useCallback } from 'react';

interface AgentModeProps {
  sessionToken: string;
  currentCode?: string;
  onResult?: (result: AgentResult) => void;
}

interface AgentResult {
  success: boolean;
  status: string;
  result: string;
  iterations: number;
}

interface LogEntry {
  timestamp: Date;
  message: string;
  type: 'info' | 'success' | 'error';
}

export default function AgentMode({ sessionToken, currentCode, onResult }: AgentModeProps) {
  const [enabled, setEnabled] = useState(false);
  const [running, setRunning] = useState(false);
  const [taskDescription, setTaskDescription] = useState('');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [iterations, setIterations] = useState(0);
  const [status, setStatus] = useState<string>('');

  const addLog = useCallback((message: string, type: LogEntry['type'] = 'info') => {
    setLogs(prev => [...prev, { timestamp: new Date(), message, type }]);
  }, []);

  const runAgent = useCallback(async () => {
    if (!taskDescription.trim()) {
      addLog('Please enter a task description', 'error');
      return;
    }

    setRunning(true);
    setLogs([]);
    setIterations(0);
    addLog('Starting agent task...', 'info');

    try {
      const response = await fetch('/api/onboarding/agent-mode/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_token: sessionToken,
          task_description: taskDescription,
          current_code: currentCode,
        }),
      });

      const data = await response.json();

      if (data.success) {
        setStatus(data.status);
        setIterations(data.iterations || 0);
        addLog(`Agent completed with status: ${data.status}`, 'success');
        addLog(`Total iterations: ${data.iterations}`, 'info');

        if (onResult) {
          onResult(data);
        }
      } else {
        addLog(`Error: ${data.error}`, 'error');
      }
    } catch (error) {
      addLog(`Network error: ${error}`, 'error');
    } finally {
      setRunning(false);
    }
  }, [sessionToken, taskDescription, currentCode, addLog, onResult]);

  const stopAgent = useCallback(() => {
    setRunning(false);
    addLog('Agent stopped by user', 'info');
  }, [addLog]);

  if (!enabled) {
    return (
      <div style={{ padding: '16px', borderRadius: '8px', backgroundColor: '#f8f9fa', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600 }}>Agent Mode</h3>
            <p style={{ margin: '4px 0 0', fontSize: '12px', color: '#666' }}>
              Autonomous debugging and iteration
            </p>
          </div>
          <button
            onClick={() => setEnabled(true)}
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: '#007bff',
              color: 'white',
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            Enable
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: '16px', borderRadius: '8px', backgroundColor: '#f8f9fa', marginBottom: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600 }}>Agent Mode</h3>
        <button
          onClick={() => setEnabled(false)}
          style={{
            padding: '4px 8px',
            borderRadius: '4px',
            border: '1px solid #ddd',
            backgroundColor: 'white',
            cursor: 'pointer',
            fontSize: '12px',
          }}
        >
          Disable
        </button>
      </div>

      <textarea
        value={taskDescription}
        onChange={(e) => setTaskDescription(e.target.value)}
        placeholder="Describe the task for the agent..."
        disabled={running}
        style={{
          width: '100%',
          padding: '10px',
          borderRadius: '6px',
          border: '1px solid #ddd',
          marginBottom: '12px',
          resize: 'vertical',
          minHeight: '80px',
          fontSize: '13px',
        }}
      />

      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
        {!running ? (
          <button
            onClick={runAgent}
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: '#28a745',
              color: 'white',
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            Run Agent
          </button>
        ) : (
          <button
            onClick={stopAgent}
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: '#dc3545',
              color: 'white',
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            Stop
          </button>
        )}
      </div>

      {running && (
        <div style={{ marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <div
              style={{
                width: '16px',
                height: '16px',
                border: '2px solid #007bff',
                borderTopColor: 'transparent',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
              }}
            />
            <span style={{ fontSize: '13px' }}>Running... Iteration {iterations}</span>
          </div>
          <div style={{ height: '4px', backgroundColor: '#e9ecef', borderRadius: '2px' }}>
            <div
              style={{
                height: '100%',
                backgroundColor: '#007bff',
                borderRadius: '2px',
                width: `${Math.min(iterations * 10, 100)}%`,
                transition: 'width 0.3s',
              }}
            />
          </div>
        </div>
      )}

      {status && (
        <div style={{ marginBottom: '12px', padding: '8px', backgroundColor: status === 'complete' ? '#d4edda' : '#fff3cd', borderRadius: '6px' }}>
          <span style={{ fontSize: '13px', fontWeight: 500 }}>Status: {status}</span>
        </div>
      )}

      {logs.length > 0 && (
        <div
          style={{
            maxHeight: '200px',
            overflowY: 'auto',
            backgroundColor: '#1e1e1e',
            borderRadius: '6px',
            padding: '8px',
            fontFamily: 'monospace',
            fontSize: '12px',
          }}
        >
          {logs.map((log, i) => (
            <div
              key={i}
              style={{
                color: log.type === 'error' ? '#ff6b6b' : log.type === 'success' ? '#51cf66' : '#adb5bd',
                marginBottom: '4px',
              }}
            >
              [{log.timestamp.toLocaleTimeString()}] {log.message}
            </div>
          ))}
        </div>
      )}

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
