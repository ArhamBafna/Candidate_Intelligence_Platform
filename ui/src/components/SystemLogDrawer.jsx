import React, { useState, useEffect } from 'react';
import { Gear, MagnifyingGlass, FileText, ChartBar, Timer, Warning } from '@phosphor-icons/react';

export default function SystemLogDrawer() {
  const [isOpen, setIsOpen] = useState(false);
  const [logs, setLogs] = useState([]);
  const [status, setStatus] = useState('normal');
  const [activeFilter, setActiveFilter] = useState('all');
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchLogs = async () => {
    try {
      const res = await fetch('/api/logs');
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs || []);
        setStatus(data.status || 'normal');
      }
    } catch (err) {
      // Background poll fail silence
    }
  };

  useEffect(() => {
    fetchLogs();
    if (!autoRefresh) return;
    const interval = setInterval(fetchLogs, 3000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const warningCount = logs.filter(
    l => l.level === 'warning' || l.level === 'error' || (l.event && (l.event.includes('warning') || l.event.includes('failed') || l.status === 'skipped'))
  ).length;

  const filteredLogs = logs.filter(log => {
    if (activeFilter === 'warnings') {
      return log.level === 'warning' || log.level === 'error' || log.status === 'skipped' || (log.event && log.event.includes('failed'));
    }
    if (activeFilter === 'uploads') {
      return log.event === 'resume_upload_complete' || (log.path && log.path.includes('upload'));
    }
    if (activeFilter === 'searches') {
      return log.event === 'candidate_search_complete' || (log.path && log.path.includes('search'));
    }
    return true;
  });

  const getBadgeStyle = (log) => {
    if (log.level === 'error' || log.status === 'failed' || (log.event && log.event.includes('failed'))) {
      return { bg: '#fee2e2', text: '#dc2626', border: '#fca5a5', label: 'ERROR / FAILED' };
    }
    if (log.level === 'warning' || log.status === 'skipped' || (log.event && log.event.includes('skipped'))) {
      return { bg: '#fef3c7', text: '#d97706', border: '#fcd34d', label: log.skip_reason ? `SKIPPED (${log.skip_reason})` : 'WARNING / SKIPPED' };
    }
    return { bg: '#dcfce7', text: '#16a34a', border: '#86efac', label: 'SUCCESS / OK' };
  };

  return (
    <div style={{ position: 'fixed', bottom: '20px', right: '20px', zIndex: 9999, fontFamily: 'Roboto, sans-serif' }}>
      {/* Floating Status Pill */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 16px',
            borderRadius: '9999px',
            background: warningCount > 0 ? '#451a03' : '#064e3b',
            color: warningCount > 0 ? '#fde68a' : '#a7f3d0',
            border: `1.5px solid ${warningCount > 0 ? '#f59e0b' : '#10b981'}`,
            boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.3)',
            cursor: 'pointer',
            fontWeight: 600,
            fontSize: '13px',
            transition: 'all 0.2s ease-in-out'
          }}
        >
          <span style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            backgroundColor: warningCount > 0 ? '#f59e0b' : '#10b981',
            boxShadow: `0 0 10px ${warningCount > 0 ? '#f59e0b' : '#10b981'}`
          }} />
          {warningCount > 0 ? `System Telemetry (${warningCount} Warning${warningCount > 1 ? 's' : ''})` : 'System Telemetry (Operational)'}
        </button>
      )}

      {/* Drawer Panel */}
      {isOpen && (
        <div style={{
          width: '440px',
          maxHeight: '580px',
          borderRadius: '16px',
          background: '#0f172a', /* Solid slate-900 */
          border: '1px solid rgba(255, 255, 255, 0.15)',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          color: '#f8fafc'
        }}>
          {/* Drawer Header */}
          <div style={{
            padding: '14px 18px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(30, 41, 59, 1)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '18px', display: 'flex' }}><Gear /></span>
              <span style={{ fontWeight: 700, fontSize: '14px', letterSpacing: '-0.01em', fontFamily: 'Outfit, sans-serif' }}>System Activity Console</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                style={{
                  fontSize: '11px',
                  padding: '3px 8px',
                  borderRadius: '6px',
                  background: autoRefresh ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.1)',
                  color: autoRefresh ? '#34d399' : '#94a3b8',
                  border: 'none',
                  cursor: 'pointer'
                }}
              >
                {autoRefresh ? 'Live' : 'Paused'}
              </button>
              <button
                onClick={() => setIsOpen(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#94a3b8',
                  fontSize: '18px',
                  cursor: 'pointer',
                  padding: '0 4px'
                }}
              >
                ✕
              </button>
            </div>
          </div>

          {/* Filter Tabs */}
          <div style={{
            display: 'flex',
            gap: '4px',
            padding: '8px 12px',
            background: 'rgba(15, 23, 42, 0.6)',
            borderBottom: '1px solid rgba(255, 255, 255, 0.05)'
          }}>
            {[
              { id: 'all', label: `All (${logs.length})` },
              { id: 'warnings', label: `Warnings (${warningCount})` },
              { id: 'uploads', label: 'Uploads' },
              { id: 'searches', label: 'Searches' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveFilter(tab.id)}
                style={{
                  padding: '5px 10px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 500,
                  border: 'none',
                  cursor: 'pointer',
                  background: activeFilter === tab.id ? 'rgba(59, 130, 246, 0.25)' : 'transparent',
                  color: activeFilter === tab.id ? '#60a5fa' : '#94a3b8'
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Log Event Stream Container */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            maxHeight: '440px'
          }}>
            {filteredLogs.length === 0 ? (
              <div style={{ padding: '30px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
                No events recorded in telemetry buffer yet.
              </div>
            ) : (
              filteredLogs.map((log, idx) => {
                const badge = getBadgeStyle(log);
                return (
                  <div
                    key={idx}
                    style={{
                      padding: '10px 12px',
                      borderRadius: '8px',
                      background: 'rgba(30, 41, 59, 0.4)',
                      border: '1px solid rgba(255, 255, 255, 0.06)',
                      fontSize: '12px',
                      lineHeight: '1.4'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 600, color: '#e2e8f0' }}>{log.event || 'http_request'}</span>
                      <span style={{
                        fontSize: '10px',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontWeight: 700,
                        background: badge.bg,
                        color: badge.text,
                        border: `1px solid ${badge.border}`
                      }}>
                        {badge.label}
                      </span>
                    </div>

                    {/* Metadata details */}
                    <div style={{ color: '#94a3b8', fontSize: '11px', display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '6px' }}>
                      {log.query && <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><MagnifyingGlass size={12}/> Query: <span style={{ color: '#cbd5e1' }}>"{log.query}"</span></div>}
                      {log.file_hash && <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><FileText size={12}/> Hash: <code style={{ color: '#93c5fd' }}>{log.file_hash.substring(0, 16)}...</code></div>}
                      {log.candidates_returned !== undefined && <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><ChartBar size={12}/> Returned: <span style={{ color: '#cbd5e1' }}>{log.candidates_returned} candidates</span></div>}
                      {log.total_duration_ms !== undefined && <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Timer size={12}/> Latency: <span style={{ color: '#34d399' }}>{log.total_duration_ms} ms</span> (vector: {log.vector_search_duration_ms}ms, db: {log.db_retrieval_duration_ms}ms)</div>}
                      {log.error && <div style={{ color: '#fca5a5', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}><Warning size={12}/> Error: {log.error}</div>}
                      {log.timestamp && <div style={{ fontSize: '9px', color: '#475569', marginTop: '2px' }}>{new Date(log.timestamp).toLocaleTimeString()}</div>}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
