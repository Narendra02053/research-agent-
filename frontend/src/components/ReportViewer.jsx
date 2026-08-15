import { FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown'; // We might need to install this, but for now we'll use simple rendering or div

export default function ReportViewer({ report }) {
  if (!report) return null;

  return (
    <div className="bg-white rounded-2xl p-8 border border-slate-200 shadow-sm prose max-w-none">
      <div className="flex items-center gap-3 mb-6 pb-4 border-b border-slate-100">
        <FileText className="text-orange-500" size={28} />
        <h2 className="text-2xl font-extrabold text-slate-900 m-0">Final Research Report</h2>
      </div>
      
      <div className="text-slate-700 leading-relaxed font-sans">
        <ReactMarkdown>{report}</ReactMarkdown>
      </div>
    </div>
  );
}
