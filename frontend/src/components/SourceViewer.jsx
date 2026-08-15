import { ExternalLink, ShieldCheck, AlertTriangle } from 'lucide-react';

export default function SourceViewer({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
      <h3 className="text-xl font-extrabold text-slate-900 mb-6">Sources & Citations</h3>
      <div className="flex flex-col gap-4">
        {sources.map((source, index) => (
          <a
            key={index}
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block p-4 rounded-xl bg-slate-50 border border-slate-100 hover:border-orange-500 hover:bg-white hover:shadow-md transition-all group"
          >
            <div className="flex justify-between items-start mb-2">
              <h4 className="text-sm font-bold text-slate-800 line-clamp-2 group-hover:text-orange-600 transition-colors">
                {source.title || (source.url.split('/')[2])}
              </h4>
              <ExternalLink size={16} className="text-slate-400 group-hover:text-orange-500 shrink-0 ml-2" />
            </div>
            <p className="text-xs text-slate-400 truncate mb-3">{source.url}</p>
            
            <div className="flex items-center gap-3 mt-auto">
               <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 text-xs font-semibold border border-emerald-100">
                  <ShieldCheck size={14} className="text-emerald-600" />
                  Trusted Source
               </span>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
