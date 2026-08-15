import { FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown'; // We might need to install this, but for now we'll use simple rendering or div

export default function ReportViewer({ report }) {
  if (!report) return null;

  return (
    <div className="bg-gray-800 rounded-2xl p-8 border border-gray-700 shadow-xl prose prose-invert max-w-none">
      <div className="flex items-center gap-3 mb-6 pb-4 border-b border-gray-700">
        <FileText className="text-blue-500" size={28} />
        <h2 className="text-2xl font-bold text-gray-100 m-0">Final Research Report</h2>
      </div>
      
      {/* Fallback rendering if ReactMarkdown isn't installed. In a real app we'd use react-markdown */}
      <div className="text-gray-300 whitespace-pre-wrap leading-relaxed font-sans">
        {report}
      </div>
    </div>
  );
}
