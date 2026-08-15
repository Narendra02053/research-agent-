import { useState } from 'react';
import { Search, X } from 'lucide-react';

export default function ResearchForm({ onSubmit, status, onCancel }) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSubmit(query);
    }
  };

  const isRunning = status === 'pending' || status === 'running';

  return (
    <form onSubmit={handleSubmit} style={{ width: '100%', maxWidth: '780px', margin: '0 auto' }}>
      <div style={{ position: 'relative', display: 'flex', alignItems: 'stretch', gap: '0' }}>
        {/* Search icon box */}
        <div style={{
          background: '#0A0A0A',
          border: '3px solid #0A0A0A',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '0 16px',
          flexShrink: 0,
        }}>
          <Search size={20} color="#FFE500" />
        </div>

        {/* Input */}
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="What would you like to research today?"
          disabled={isRunning}
          style={{
            flex: 1,
            background: '#FAFAF0',
            border: '3px solid #0A0A0A',
            borderLeft: 'none',
            padding: '16px 18px',
            fontFamily: "'Space Grotesk', sans-serif",
            fontWeight: 500,
            fontSize: '1rem',
            color: '#0A0A0A',
            outline: 'none',
            borderRadius: 0,
            opacity: isRunning ? 0.6 : 1,
            cursor: isRunning ? 'not-allowed' : 'text',
          }}
        />

        {/* Button */}
        {isRunning ? (
          <button
            type="button"
            onClick={onCancel}
            style={{
              background: '#FF3D77',
              color: '#fff',
              border: '3px solid #0A0A0A',
              borderLeft: 'none',
              padding: '0 28px',
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 700,
              fontSize: '0.85rem',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              flexShrink: 0,
              transition: 'background 0.1s',
            }}
          >
            <X size={16} />
            CANCEL
          </button>
        ) : (
          <button
            type="submit"
            disabled={!query.trim()}
            style={{
              background: !query.trim() ? '#ccc' : '#FFE500',
              color: '#0A0A0A',
              border: '3px solid #0A0A0A',
              borderLeft: 'none',
              padding: '0 28px',
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 700,
              fontSize: '0.85rem',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              cursor: !query.trim() ? 'not-allowed' : 'pointer',
              flexShrink: 0,
              transition: 'background 0.1s',
            }}
          >
            RESEARCH →
          </button>
        )}
      </div>

      {/* Bottom shadow bar */}
      <div style={{
        height: '6px',
        background: '#0A0A0A',
        marginLeft: '0',
        boxShadow: 'none',
        transform: 'translate(6px, 0)',
        width: '100%',
      }} />
    </form>
  );
}
