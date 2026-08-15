// MetricsDashboard.jsx - Component displaying research metrics.
import { Activity, ShieldCheck, AlertOctagon, CheckCircle2 } from 'lucide-react';

export default function MetricsDashboard({ metrics }) {
  if (!metrics || Object.keys(metrics).length === 0 || metrics.overall_confidence === undefined) {
    return null;
  }

  const getScoreColor = (score, inverse = false) => {
    if (score === undefined || score === null || isNaN(score)) return { bg: '#e8e3d8', text: '#888', border: '#ccc' };
    if (inverse) {
      return score < 0.2
        ? { bg: '#B0FF3D', text: '#0A0A0A', border: '#0A0A0A' }
        : score < 0.5
        ? { bg: '#FFE500', text: '#0A0A0A', border: '#0A0A0A' }
        : { bg: '#FF3D77', text: '#fff', border: '#0A0A0A' };
    }
    return score > 0.8
      ? { bg: '#B0FF3D', text: '#0A0A0A', border: '#0A0A0A' }
      : score > 0.6
      ? { bg: '#FFE500', text: '#0A0A0A', border: '#0A0A0A' }
      : { bg: '#FF3D77', text: '#fff', border: '#0A0A0A' };
  };

  const formatValue = (val) => {
    if (val === undefined || val === null || isNaN(val)) return 'N/A';
    return `${(val * 100).toFixed(0)}%`;
  };

  const cards = [
    {
      label: 'Overall Confidence',
      value: formatValue(metrics.overall_confidence),
      icon: Activity,
      colors: getScoreColor(metrics.overall_confidence),
      tag: 'CONFIDENCE',
    },
    {
      label: 'Grounding Score',
      value: formatValue(metrics.grounding_score),
      icon: ShieldCheck,
      colors: getScoreColor(metrics.grounding_score),
      tag: 'GROUNDING',
    },
    {
      label: 'Hallucination Risk',
      value: formatValue(metrics.hallucination_risk),
      icon: AlertOctagon,
      colors: getScoreColor(metrics.hallucination_risk, true),
      tag: 'HALLUCINATION',
    },
    {
      label: 'Source Quality',
      value: formatValue(metrics.source_quality),
      icon: CheckCircle2,
      colors: getScoreColor(metrics.source_quality),
      tag: 'QUALITY',
    },
  ];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(4, 1fr)',
      gap: '16px',
      marginBottom: '8px',
    }}>
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div key={idx} style={{
            background: '#FAFAF0',
            border: '3px solid #0A0A0A',
            boxShadow: '5px 5px 0 #0A0A0A',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            transition: 'transform 0.1s, box-shadow 0.1s',
            cursor: 'default',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.transform = 'translate(-2px, -2px)';
            e.currentTarget.style.boxShadow = '7px 7px 0 #0A0A0A';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.transform = 'none';
            e.currentTarget.style.boxShadow = '5px 5px 0 #0A0A0A';
          }}
          >
            {/* Tag + icon row */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{
                background: '#0A0A0A',
                color: '#FFE500',
                fontSize: '0.6rem',
                fontWeight: 700,
                padding: '2px 8px',
                fontFamily: "'Space Mono', monospace",
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
              }}>
                {card.tag}
              </span>
              <Icon size={16} color="#0A0A0A" />
            </div>

            {/* Big value */}
            <div style={{
              fontSize: '2.4rem',
              fontWeight: 700,
              fontFamily: "'Space Mono', monospace",
              color: '#0A0A0A',
              lineHeight: 1,
            }}>
              {card.value}
            </div>

            {/* Coloured bar at bottom */}
            <div style={{
              height: '8px',
              background: card.colors.bg,
              border: `2px solid ${card.colors.border}`,
              marginTop: '4px',
            }} />

            <div style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              color: '#555',
              fontFamily: "'Space Grotesk', sans-serif",
            }}>
              {card.label}
            </div>
          </div>
        );
      })}
    </div>
  );
}
