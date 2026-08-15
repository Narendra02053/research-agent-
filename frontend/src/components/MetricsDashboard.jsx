import { Activity, ShieldCheck, AlertOctagon, CheckCircle2 } from 'lucide-react';

export default function MetricsDashboard({ metrics }) {
  if (!metrics) return null;

  const getScoreColor = (score, inverse = false) => {
    if (inverse) {
      return score < 0.2 ? 'text-green-400' : score < 0.5 ? 'text-yellow-400' : 'text-red-400';
    }
    return score > 0.8 ? 'text-green-400' : score > 0.6 ? 'text-yellow-400' : 'text-red-400';
  };

  const cards = [
    {
      label: 'Overall Confidence',
      value: `${(metrics.overall_confidence * 100).toFixed(0)}%`,
      icon: Activity,
      color: getScoreColor(metrics.overall_confidence)
    },
    {
      label: 'Grounding Score',
      value: `${(metrics.grounding_score * 100).toFixed(0)}%`,
      icon: ShieldCheck,
      color: getScoreColor(metrics.grounding_score)
    },
    {
      label: 'Hallucination Risk',
      value: `${(metrics.hallucination_risk * 100).toFixed(0)}%`,
      icon: AlertOctagon,
      color: getScoreColor(metrics.hallucination_risk, true)
    },
    {
      label: 'Source Quality',
      value: `${(metrics.source_quality * 100).toFixed(0)}%`,
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
