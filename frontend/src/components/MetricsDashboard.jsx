import { Activity, ShieldCheck, AlertOctagon, CheckCircle2 } from 'lucide-react';

export default function MetricsDashboard({ metrics }) {
  if (!metrics || Object.keys(metrics).length === 0 || metrics.overall_confidence === undefined) {
    return null;
  }

  const getScoreColor = (score, inverse = false) => {
    if (score === undefined || score === null || isNaN(score)) {
      return 'text-gray-400';
    }
    if (inverse) {
      return score < 0.2 ? 'text-green-400' : score < 0.5 ? 'text-yellow-400' : 'text-red-400';
    }
    return score > 0.8 ? 'text-green-400' : score > 0.6 ? 'text-yellow-400' : 'text-red-400';
  };

  const formatValue = (val) => {
    if (val === undefined || val === null || isNaN(val)) {
      return 'N/A';
    }
    return `${(val * 100).toFixed(0)}%`;
  };

  const cards = [
    {
      label: 'Overall Confidence',
      value: formatValue(metrics.overall_confidence),
      icon: Activity,
      color: getScoreColor(metrics.overall_confidence)
    },
    {
      label: 'Grounding Score',
      value: formatValue(metrics.grounding_score),
      icon: ShieldCheck,
      color: getScoreColor(metrics.grounding_score)
    },
    {
      label: 'Hallucination Risk',
      value: formatValue(metrics.hallucination_risk),
      icon: AlertOctagon,
      color: getScoreColor(metrics.hallucination_risk, true)
    },
    {
      label: 'Source Quality',
      value: formatValue(metrics.source_quality),
      icon: CheckCircle2,
      color: getScoreColor(metrics.source_quality)
    }
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      {cards.map((card, idx) => (
        <div key={idx} className="bg-gray-800 p-5 rounded-2xl border border-gray-700 flex flex-col shadow-lg">
          <div className="flex items-center gap-2 mb-2 text-gray-400">
            <card.icon size={16} />
            <span className="text-sm font-medium">{card.label}</span>
          </div>
          <div className={`text-3xl font-bold ${card.color}`}>
            {card.value}
          </div>
        </div>
      ))}
    </div>
  );
}
