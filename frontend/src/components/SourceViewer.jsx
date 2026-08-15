import { ExternalLink, ShieldCheck } from 'lucide-react';

export default function SourceViewer({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div style={{
      background: '#FAFAF0',
      border: '3px solid #0A0A0A',
      boxShadow: '6px 6px 0 #0A0A0A',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
    }}>
      {/* Header */}
      <div style={{
        background: '#FFE500',
        borderBottom: '3px solid #0A0A0A',
        padding: '12px 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <span style={{
          fontFamily: "'Space Grotesk', sans-serif",
          fontWeight: 700,
          fontSize: '0.85rem',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color: '#0A0A0A',
        }}>
          Sources & Citations
        </span>
        <span style={{
          background: '#0A0A0A',
          color: '#FFE500',
          fontFamily: "'Space Mono', monospace",
          fontWeight: 700,
          fontSize: '0.7rem',
          padding: '3px 10px',
          letterSpacing: '0.05em',
        }}>
          {sources.length} SRC
        </span>
      </div>

      {/* Source list */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0',
        overflowY: 'auto',
        flex: 1,
      }}>
        {sources.map((source, index) => (
          <a
            key={index}
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'block',
              padding: '16px 20px',
              borderBottom: index < sources.length - 1 ? '2px solid #0A0A0A' : 'none',
              textDecoration: 'none',
              background: '#FAFAF0',
              transition: 'background 0.1s',
              cursor: 'pointer',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = '#FFE500';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = '#FAFAF0';
            }}
          >
            {/* Index + title row */}
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', marginBottom: '6px' }}>
              <span style={{
                background: '#0A0A0A',
                color: '#FFE500',
                fontFamily: "'Space Mono', monospace",
                fontWeight: 700,
                fontSize: '0.65rem',
                padding: '2px 6px',
                flexShrink: 0,
                marginTop: '2px',
              }}>
                {String(index + 1).padStart(2, '0')}
              </span>
              <span style={{
                fontFamily: "'Space Grotesk', sans-serif",
                fontWeight: 700,
                fontSize: '0.85rem',
                color: '#0A0A0A',
                lineHeight: 1.3,
                flex: 1,
                overflow: 'hidden',
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
              }}>
                {source.title || source.url.split('/')[2]}
              </span>
              <ExternalLink size={14} color="#888" style={{ flexShrink: 0, marginTop: 2 }} />
            </div>

            {/* URL */}
            <p style={{
              fontFamily: "'Space Mono', monospace",
              fontSize: '0.65rem',
              color: '#888',
              margin: '0 0 8px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              paddingLeft: '34px',
            }}>
              {source.url}
            </p>

            {/* Badge */}
            <div style={{ paddingLeft: '34px' }}>
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                background: '#B0FF3D',
                color: '#0A0A0A',
                border: '2px solid #0A0A0A',
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '2px 8px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                fontFamily: "'Space Grotesk', sans-serif",
              }}>
                <ShieldCheck size={11} />
                Verified
              </span>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
