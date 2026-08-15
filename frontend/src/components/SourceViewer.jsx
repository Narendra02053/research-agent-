import { ExternalLink, ShieldCheck, AlertTriangle } from 'lucide-react';

export default function SourceViewer({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700 shadow-xl">
      <h3 className="text-xl font-semibold text-gray-100 mb-6">Sources & Citations</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sources.map((source, index) => (
          <a
            key={index}
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block p-4 rounded-xl bg-gray-900 border border-gray-700 hover:border-blue-500 hover:bg-gray-800 transition-all group"
          >
            <div className="flex justify-between items-start mb-2">
              <h4 className="text-sm font-medium text-gray-200 line-clamp-2 group-hover:text-blue-400 transition-colors">
                {source.title || (source.url.split('/')[2])}
              </h4>
              <ExternalLink size={16} className="text-gray-500 group-hover:text-blue-400 shrink-0 ml-2" />
            </div>
            <p className="text-xs text-gray-500 truncate mb-3">{source.url}</p>
            
            <div className="flex items-center gap-3 mt-auto">
               <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-green-500/10 text-green-400 text-xs font-medium">
                  <ShieldCheck size={14} />
                  Trusted
               </span>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
