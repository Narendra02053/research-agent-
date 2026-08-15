import { useResearchStream } from '../hooks/useResearchStream';
import ResearchForm from '../components/ResearchForm';
import WorkflowTimeline from '../components/research/WorkflowTimeline';
import LiveResearchFeed from '../components/research/LiveResearchFeed';
import ReportViewer from '../components/ReportViewer';
import SourceViewer from '../components/SourceViewer';
import MetricsDashboard from '../components/MetricsDashboard';
import { AlertCircle, Beaker } from 'lucide-react';

export default function Dashboard() {
  const { status, progress, currentStep, result, error, events, submitQuery, cancelJob } = useResearchStream();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans selection:bg-orange-500/20">
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur-md sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-blue-600 to-orange-500 p-2 rounded-xl shadow-sm">
              <Beaker size={24} className="text-white" />
            </div>
            <h1 className="text-xl font-extrabold tracking-tight text-slate-900">
              AI Deep <span className="text-orange-500">Research</span>
            </h1>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              <div className={`w-2.5 h-2.5 rounded-full ${status === 'running' ? 'bg-orange-500 animate-pulse' : 'bg-emerald-500'}`} />
              <span className="text-slate-600">{status === 'running' ? 'Streaming...' : 'System Online'}</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-12">
          <h2 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 via-indigo-600 to-orange-500 mb-4 tracking-tight">
            Live AI Research Engine
          </h2>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto font-medium">
            Experience real-time LLM reasoning and retrieval updates via WebSockets.
          </p>
        </div>

        <ResearchForm onSubmit={submitQuery} status={status} onCancel={cancelJob} />

        {error && (
          <div className="max-w-3xl mx-auto mt-8 p-4 rounded-2xl bg-red-50 border border-red-200 flex items-start gap-3 shadow-sm">
            <AlertCircle className="text-red-500 shrink-0 mt-0.5" size={20} />
            <p className="text-red-700 text-sm leading-relaxed font-medium">{error}</p>
          </div>
        )}

        {(status === 'pending' || status === 'running') && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
            <WorkflowTimeline progress={progress} currentStep={currentStep} />
            <LiveResearchFeed events={events} />
          </div>
        )}

        {status === 'completed' && result && (
          <div className="mt-12 animate-in fade-in slide-in-from-bottom-8 duration-700 space-y-8">
            <MetricsDashboard metrics={result.quality_metrics} />
            
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
              <div className="xl:col-span-2">
                <ReportViewer report={result.report} />
              </div>
              <div className="xl:col-span-1">
                <SourceViewer sources={result.sources} />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
