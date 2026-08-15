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
    <div className="min-h-screen bg-gray-950 text-gray-100 font-sans selection:bg-blue-500/30">
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-blue-600 p-2 rounded-lg">
              <Beaker size={24} className="text-white" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-white">AI Deep Research</h1>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm">
              <div className={`w-2 h-2 rounded-full ${status === 'running' ? 'bg-blue-500 animate-pulse' : 'bg-green-500'}`} />
              <span className="text-gray-400">{status === 'running' ? 'Streaming...' : 'System Online'}</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-12">
          <h2 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400 mb-4 tracking-tight">
            Live AI Research Engine
          </h2>
          <p className="text-lg text-gray-400 max-w-2xl mx-auto">
            Experience real-time LLM reasoning and retrieval updates via WebSockets.
          </p>
        </div>

        <ResearchForm onSubmit={submitQuery} status={status} onCancel={cancelJob} />

        {error && (
          <div className="max-w-3xl mx-auto mt-8 p-4 rounded-xl bg-red-900/20 border border-red-500/50 flex items-start gap-3">
            <AlertCircle className="text-red-400 shrink-0 mt-0.5" size={20} />
            <p className="text-red-200 text-sm leading-relaxed">{error}</p>
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
