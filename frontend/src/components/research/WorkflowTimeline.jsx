import { motion } from 'framer-motion';
import { Loader2, CheckCircle, Search, FileText, Database, GitMerge, FileSearch } from 'lucide-react';

const steps = [
  { id: 'initializing', label: 'Init', icon: Loader2, accent: '#FFE500' },
  { id: 'planner', label: 'Plan', icon: FileText, accent: '#3DFFE8' },
  { id: 'search', label: 'Search', icon: Search, accent: '#B0FF3D' },
  { id: 'retrieval', label: 'Retrieve', icon: Database, accent: '#FFE500' },
  { id: 'analysis', label: 'Synth', icon: GitMerge, accent: '#FF6B35' },
  { id: 'report', label: 'Draft', icon: FileText, accent: '#3DFFE8' },
  { id: 'evaluation', label: 'Evaluate', icon: FileSearch, accent: '#B0FF3D' },
  { id: 'done', label: 'Done', icon: CheckCircle, accent: '#B0FF3D' },
];

export default function WorkflowTimeline({ progress, currentStep }) {
  const currentStepIndex = steps.findIndex(s => s.id === currentStep);
  const activeIndex = currentStepIndex === -1 ? 0 : currentStepIndex;

  return (
    <div style={{
      width: '100%',
      maxWidth: '860px',
      margin: '32px auto 0',
      background: '#FAFAF0',
      border: '3px solid #0A0A0A',
      boxShadow: '6px 6px 0 #0A0A0A',
    }}>
      {/* Header */}
      <div style={{
        background: '#0A0A0A',
        padding: '12px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Loader2
            size={18}
            color="#FFE500"
            style={{ animation: 'spin 1s linear infinite' }}
          />
          <span style={{
            color: '#FFE500',
            fontFamily: "'Space Grotesk', sans-serif",
            fontWeight: 700,
            fontSize: '0.85rem',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
          }}>
            Research in Progress
          </span>
        </div>
        <span style={{
          color: '#FF3D77',
          fontFamily: "'Space Mono', monospace",
          fontWeight: 700,
          fontSize: '1.4rem',
          letterSpacing: '-0.02em',
        }}>
          {progress}%
        </span>
      </div>

      <div style={{ padding: '24px' }}>
        {/* Progress bar */}
        <div style={{
          height: '12px',
          background: '#e8e3d8',
          border: '2px solid #0A0A0A',
          marginBottom: '24px',
          position: 'relative',
          overflow: 'hidden',
        }}>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.4 }}
            style={{
              height: '100%',
              background: '#FFE500',
              borderRight: progress < 100 ? '2px solid #0A0A0A' : 'none',
            }}
          />
        </div>

        {/* Steps */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '12px',
        }}>
          {steps.map((step, index) => {
            const Icon = step.icon;
            const isCompleted = index < activeIndex;
            const isActive = index === activeIndex;
            const isPending = index > activeIndex;

            let bg = '#F5F0E8';
            let iconColor = '#888';
            let labelColor = '#888';
            let border = '2px solid #ccc';
            let shadow = 'none';

            if (isCompleted) {
              bg = '#B0FF3D';
              iconColor = '#0A0A0A';
              labelColor = '#0A0A0A';
              border = '2px solid #0A0A0A';
              shadow = '3px 3px 0 #0A0A0A';
            } else if (isActive) {
              bg = '#FFE500';
              iconColor = '#0A0A0A';
              labelColor = '#0A0A0A';
              border = '2px solid #0A0A0A';
              shadow = '3px 3px 0 #FF3D77';
            }

            return (
              <div key={step.id} style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 8px',
                background: bg,
                border: border,
                boxShadow: shadow,
                transition: 'all 0.2s',
              }}>
                <Icon
                  size={20}
                  color={iconColor}
                  style={{
                    animation: isActive ? 'spin 1s linear infinite' : 'none',
                  }}
                />
                <span style={{
                  color: labelColor,
                  fontFamily: "'Space Grotesk', sans-serif",
                  fontWeight: 700,
                  fontSize: '0.7rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  textAlign: 'center',
                }}>
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
