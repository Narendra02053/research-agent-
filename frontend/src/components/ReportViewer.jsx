// ReportViewer.jsx - Component for viewing generated reports.
import { FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export default function ReportViewer({ report }) {
  if (!report) return null;

  return (
    <div style={{
      background: '#FAFAF0',
      border: '3px solid #0A0A0A',
      boxShadow: '6px 6px 0 #0A0A0A',
    }}>
      {/* Header bar */}
      <div style={{
        background: '#0A0A0A',
        padding: '12px 24px',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        borderBottom: '3px solid #0A0A0A',
      }}>
        <div style={{
          background: '#FF3D77',
          border: '2px solid #FF3D77',
          padding: '4px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <FileText size={16} color="#fff" />
        </div>
        <span style={{
          color: '#FAFAF0',
          fontFamily: "'Space Grotesk', sans-serif",
          fontWeight: 700,
          fontSize: '0.85rem',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
        }}>
          Final Research Report
        </span>
        <div style={{ marginLeft: 'auto' }}>
          <span style={{
            background: '#FFE500',
            color: '#0A0A0A',
            fontSize: '0.65rem',
            fontWeight: 700,
            padding: '3px 10px',
            fontFamily: "'Space Mono', monospace",
            letterSpacing: '0.08em',
            border: '1px solid #0A0A0A',
            textTransform: 'uppercase',
          }}>
            COMPLETE
          </span>
        </div>
      </div>

      {/* Report body */}
      <div style={{
        padding: '32px',
        fontFamily: "'Space Grotesk', sans-serif",
        color: '#1a1a1a',
        lineHeight: 1.75,
      }}
        className="prose max-w-none"
      >
        <ReactMarkdown>{report}</ReactMarkdown>
      </div>
    </div>
  );
}
