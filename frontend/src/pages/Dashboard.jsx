import { useResearchStream } from '../hooks/useResearchStream';
import ResearchForm from '../components/ResearchForm';
import WorkflowTimeline from '../components/research/WorkflowTimeline';
import LiveResearchFeed from '../components/research/LiveResearchFeed';
import ReportViewer from '../components/ReportViewer';
import SourceViewer from '../components/SourceViewer';
import MetricsDashboard from '../components/MetricsDashboard';
import { AlertCircle, Beaker, Zap } from 'lucide-react';

export default function Dashboard() {
  const { status, progress, currentStep, result, error, events, submitQuery, cancelJob } = useResearchStream();

  return (
    <div className="min-h-screen" style={{ background: '#F5F0E8', fontFamily: "'Space Grotesk', sans-serif" }}>

      {/* Top accent stripe */}
      <div className="nb-stripe" />

      {/* Header */}
      <header style={{
        background: '#FFE500',
        borderBottom: '3px solid #0A0A0A',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: '64px' }}>
            {/* Logo */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{
                background: '#0A0A0A',
                border: '3px solid #0A0A0A',
                boxShadow: '3px 3px 0 #FF3D77',
                padding: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <Beaker size={22} color="#FFE500" />
              </div>
              <h1 style={{ fontSize: '1.3rem', fontWeight: 700, color: '#0A0A0A', margin: 0, letterSpacing: '-0.03em' }}>
                AI <span style={{ background: '#FF3D77', color: '#fff', padding: '0 6px' }}>DEEP</span> RESEARCH
              </h1>
            </div>

            {/* Status pill */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: '#0A0A0A',
              border: '2px solid #0A0A0A',
              padding: '6px 14px',
              boxShadow: '3px 3px 0 #0A0A0A',
            }}>
              <div style={{
                width: 10, height: 10,
                background: status === 'running' ? '#FF6B35' : '#B0FF3D',
                border: '2px solid #F5F0E8',
                borderRadius: '50%',
                animation: status === 'running' ? 'nb-blink 1s step-end infinite' : 'none',
              }} />
              <span style={{ color: '#FFE500', fontWeight: 700, fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                {status === 'running' ? 'STREAMING' : 'ONLINE'}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '48px 24px' }}>

        {/* Hero section */}
        <div style={{ textAlign: 'center', marginBottom: '48px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <span className="nb-badge-pink" style={{
              background: '#FF3D77',
              color: '#fff',
              border: '2px solid #0A0A0A',
              padding: '4px 12px',
              fontWeight: 700,
              fontSize: '0.75rem',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
            }}>
              <Zap size={12} style={{ display: 'inline', marginRight: 4 }} />
              Live Engine
            </span>
          </div>
          <h2 style={{
            fontSize: 'clamp(2.5rem, 5vw, 4rem)',
            fontWeight: 700,
            color: '#0A0A0A',
            margin: '0 0 8px',
            letterSpacing: '-0.04em',
            lineHeight: 1,
          }}>
            LIVE AI RESEARCH{' '}
            <span style={{
              background: '#FFE500',
              display: 'inline-block',
              padding: '0 8px',
              border: '3px solid #0A0A0A',
              boxShadow: '4px 4px 0 #0A0A0A',
              transform: 'rotate(-1deg)',
              display: 'inline-block',
            }}>ENGINE</span>
          </h2>
          <p style={{ color: '#444', fontSize: '1rem', fontWeight: 500, marginTop: '20px', maxWidth: '520px', margin: '20px auto 0' }}>
            Real-time LLM reasoning and retrieval updates via WebSockets.
          </p>
        </div>

        {/* Search form */}
        <ResearchForm onSubmit={submitQuery} status={status} onCancel={cancelJob} />

        {/* Error state */}
        {error && (
          <div style={{
            maxWidth: '720px',
            margin: '24px auto 0',
            padding: '16px 20px',
            background: '#FF3D77',
            border: '3px solid #0A0A0A',
            boxShadow: '5px 5px 0 #0A0A0A',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '12px',
          }} className="nb-animate-in">
            <AlertCircle color="#fff" size={20} style={{ flexShrink: 0, marginTop: 2 }} />
            <p style={{ color: '#fff', fontWeight: 600, margin: 0, fontSize: '0.9rem' }}>{error}</p>
          </div>
        )}

        {/* Running state */}
        {(status === 'pending' || status === 'running') && (
          <div className="nb-animate-in" style={{ marginTop: '32px' }}>
            <WorkflowTimeline progress={progress} currentStep={currentStep} />
            <LiveResearchFeed events={events} />
          </div>
        )}

        {/* Completed state */}
        {status === 'completed' && result && (
          <div className="nb-animate-in" style={{ marginTop: '48px' }}>
            {/* Quality metrics label */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              marginBottom: '16px',
            }}>
              <div style={{
                background: '#B0FF3D',
                border: '3px solid #0A0A0A',
                boxShadow: '3px 3px 0 #0A0A0A',
                padding: '4px 14px',
                fontWeight: 700,
                fontSize: '0.8rem',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
              }}>
                Quality Metrics
              </div>
              <div style={{ flex: 1, borderTop: '2px dashed #0A0A0A' }} />
            </div>

            <MetricsDashboard metrics={result.quality_metrics} />

            {/* Report label */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              margin: '32px 0 16px',
            }}>
              <div style={{
                background: '#FF3D77',
                color: '#fff',
                border: '3px solid #0A0A0A',
                boxShadow: '3px 3px 0 #0A0A0A',
                padding: '4px 14px',
                fontWeight: 700,
                fontSize: '0.8rem',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
              }}>
                Research Output
              </div>
              <div style={{ flex: 1, borderTop: '2px dashed #0A0A0A' }} />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) minmax(0, 1fr)', gap: '24px' }}>
                <ReportViewer report={result.report} />
                <SourceViewer sources={result.sources} />
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Bottom accent stripe */}
      <div className="nb-stripe" style={{ marginTop: '64px' }} />
    </div>
  );
}
