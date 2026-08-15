import { motion } from 'framer-motion';
import { Loader2, CheckCircle, Search, FileText, Database, GitMerge, FileSearch } from 'lucide-react';

const steps = [
  { id: 'initializing', label: 'Initializing', icon: Loader2 },
  { id: 'planner', label: 'Planning', icon: FileText },
  { id: 'search', label: 'Searching Web', icon: Search },
  { id: 'retrieval', label: 'Retrieving Knowledge', icon: Database },
  { id: 'analysis', label: 'Synthesizing Data', icon: GitMerge },
  { id: 'report', label: 'Drafting Report', icon: FileText },
  { id: 'evaluation', label: 'Evaluating Quality', icon: FileSearch },
  { id: 'done', label: 'Complete', icon: CheckCircle },
];

export default function WorkflowTimeline({ progress, currentStep }) {
  const currentStepIndex = steps.findIndex(s => s.id === currentStep);
  const activeIndex = currentStepIndex === -1 ? 0 : currentStepIndex;

  return (
    <div className="w-full max-w-4xl mx-auto bg-gray-800 rounded-2xl p-8 border border-gray-700 shadow-xl mt-8">
      <div className="flex items-center justify-between mb-8">
        <h3 className="text-xl font-semibold text-gray-100 flex items-center gap-3">
          <Loader2 className="animate-spin text-blue-500" />
          Research in Progress
        </h3>
        <span className="text-3xl font-bold text-blue-400">{progress}%</span>
      </div>

      <div className="relative">
        <div className="overflow-hidden h-2 mb-8 text-xs flex rounded-full bg-gray-700">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
            className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-blue-500"
          ></motion.div>
        </div>

        <div className="grid grid-cols-4 lg:grid-cols-8 gap-4">
          {steps.map((step, index) => {
            const Icon = step.icon;
            const isCompleted = index < activeIndex;
            const isActive = index === activeIndex;

            let colorClass = 'text-gray-500';
            let bgClass = 'bg-gray-800';
            
            if (isCompleted) {
              colorClass = 'text-green-400';
              bgClass = 'bg-green-400/10';
            } else if (isActive) {
              colorClass = 'text-blue-400';
              bgClass = 'bg-blue-400/10';
            }

            return (
              <div key={step.id} className="flex flex-col items-center text-center gap-2">
                <div className={`p-3 rounded-full ${bgClass} ${isActive ? 'ring-2 ring-blue-500' : ''}`}>
                  <Icon className={`${colorClass} ${isActive ? 'animate-pulse' : ''}`} size={24} />
                </div>
                <span className={`text-xs font-medium ${isActive ? 'text-blue-400' : 'text-gray-400'}`}>
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
