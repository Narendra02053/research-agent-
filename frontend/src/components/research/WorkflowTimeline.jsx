import { motion } from 'framer-motion';
import { Loader2, CheckCircle, Search, FileText, Database, GitMerge, FileSearch } from 'lucide-react';

const steps = [
  { id: 'initializing', label: 'Initializing', icon: Loader2 },
  { id: 'planner', label: 'Planning', icon: FileText },
  { id: 'search', label: 'Searching Web', icon: Search },
  { id: 'retrieval', label: 'Retrieving Knowledge', icon: Database },
  { id: 'analysis', label: 'Synthesizing', icon: GitMerge },
  { id: 'report', label: 'Drafting Report', icon: FileText },
  { id: 'evaluation', label: 'Evaluating', icon: FileSearch },
  { id: 'done', label: 'Complete', icon: CheckCircle },
];

export default function WorkflowTimeline({ progress, currentStep }) {
  const currentStepIndex = steps.findIndex(s => s.id === currentStep);
  const activeIndex = currentStepIndex === -1 ? 0 : currentStepIndex;

  return (
    <div className="w-full max-w-4xl mx-auto bg-white rounded-2xl p-8 border border-slate-200 shadow-sm mt-8">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-extrabold text-slate-900 flex items-center gap-3">
          <Loader2 className="animate-spin text-blue-600" size={22} />
          Research in Progress
        </h3>
        <span className="text-2xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-orange-500">
          {progress}%
        </span>
      </div>

      {/* Progress Bar */}
      <div className="relative">
        <div className="overflow-hidden h-2.5 mb-8 rounded-full bg-slate-100">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
            className="h-full rounded-full bg-gradient-to-r from-blue-600 to-orange-500 shadow-sm"
          />
        </div>

        <div className="grid grid-cols-4 lg:grid-cols-8 gap-3">
          {steps.map((step, index) => {
            const Icon = step.icon;
            const isCompleted = index < activeIndex;
            const isActive = index === activeIndex;

            let iconColor = 'text-slate-400';
            let bgClass = 'bg-slate-50';
            let ringClass = '';
            let labelColor = 'text-slate-400';

            if (isCompleted) {
              iconColor = 'text-emerald-600';
              bgClass = 'bg-emerald-50';
              labelColor = 'text-emerald-700';
            } else if (isActive) {
              iconColor = 'text-blue-600';
              bgClass = 'bg-blue-50';
              ringClass = 'ring-2 ring-blue-500 ring-offset-2';
              labelColor = 'text-blue-600';
            }

            return (
              <div key={step.id} className="flex flex-col items-center text-center gap-2">
                <div className={`p-3 rounded-full ${bgClass} ${ringClass} transition-all`}>
                  <Icon
                    className={`${iconColor} ${isActive ? 'animate-pulse' : ''}`}
                    size={22}
                  />
                </div>
                <span className={`text-xs font-semibold ${labelColor}`}>
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
