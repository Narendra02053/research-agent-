import { useEffect, useRef } from 'react';
import { Terminal } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const EVENT_COLORS = {
  'agent_start': '#B0FF3D',
  'tool_call': '#3DFFE8',
  'llm_response': '#FFE500',
  'search': '#FF6B35',
  'error': '#FF3D77',
};

export default function LiveResearchFeed({ events }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div style={{
      background: '#0A0A0A',
      border: '3px solid #0A0A0A',
      boxShadow: '6px 6px 0 #B0FF3D',
      maxWidth: '860px',
      margin: '24px auto 0',
      fontFamily: "'Space Mono', monospace",
    }}>
      {/* Terminal header */}
      <div style={{
        background: '#1a1a1a',
        borderBottom: '3px solid #0A0A0A',
        padding: '10px 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Traffic light dots — brutalist style: square, not round */}
          <div style={{ display: 'flex', gap: '6px' }}>
            <div style={{ width: 12, height: 12, background: '#FF3D77', border: '2px solid #444' }} />
            <div style={{ width: 12, height: 12, background: '#FFE500', border: '2px solid #444' }} />
            <div style={{ width: 12, height: 12, background: '#B0FF3D', border: '2px solid #444' }} />
          </div>
          <Terminal size={14} color="#666" />
          <span style={{
            color: '#555',
            fontSize: '0.7rem',
            textTransform: 'uppercase',
            letterSpacing: '0.12em',
            fontWeight: 700,
          }}>
            live_event_stream.log
          </span>
        </div>
        <span style={{
          background: '#B0FF3D',
          color: '#0A0A0A',
          fontSize: '0.65rem',
          fontWeight: 700,
          padding: '2px 8px',
          border: '1px solid #0A0A0A',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
        }}>
          {events.length} events
        </span>
      </div>

      {/* Log body */}
      <div
        ref={scrollRef}
        style={{
          padding: '16px',
          height: '280px',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
        }}
      >
        <AnimatePresence>
          {events.length === 0 && (
            <div style={{ color: '#444', fontSize: '0.75rem', fontStyle: 'italic' }}>
              <span style={{ color: '#B0FF3D' }}>$</span>{' '}
              <span className="nb-blink" style={{ color: '#666' }}>waiting for connection...</span>
            </div>
          )}

          {events.map((evt, idx) => {
            const evtColor = EVENT_COLORS[evt.event_type] || '#aaa';
            return (
              <motion.div
                key={idx}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.15 }}
                style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', lineHeight: 1.5 }}
              >
                <span style={{ color: '#444', fontSize: '0.7rem', flexShrink: 0, marginTop: '1px' }}>
                  [{new Date(evt.timestamp * 1000).toLocaleTimeString()}]
                </span>
                <span style={{
                  color: evtColor,
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  flexShrink: 0,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  marginTop: '1px',
                }}>
                  {evt.event_type}
                </span>
                <span style={{
                  color: '#ccc',
                  fontSize: '0.7rem',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  maxWidth: '420px',
                }}>
                  {JSON.stringify(evt.data)}
                </span>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
