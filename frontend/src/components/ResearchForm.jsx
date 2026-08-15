import { useState } from 'react';
import { Search, Loader2 } from 'lucide-react';

export default function ResearchForm({ onSubmit, status, onCancel }) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSubmit(query);
    }
  };

  const isRunning = status === 'pending' || status === 'running';

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-3xl mx-auto">
      <div className="relative flex items-center">
        <Search className="absolute left-4 text-slate-400" size={20} />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="What would you like to research today?"
          disabled={isRunning}
          className="w-full bg-white border border-slate-200 rounded-full py-4 pl-12 pr-32 text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent disabled:opacity-50 transition-all shadow-md"
        />
        {isRunning ? (
          <button
            type="button"
            onClick={onCancel}
            className="absolute right-2 bg-red-500 hover:bg-red-600 text-white rounded-full px-6 py-2 text-sm font-medium transition-colors"
          >
            Cancel
          </button>
        ) : (
          <button
            type="submit"
            disabled={!query.trim()}
            className="absolute right-2 bg-gradient-to-r from-blue-600 to-orange-500 hover:from-blue-700 hover:to-orange-600 text-white rounded-full px-6 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
          >
            Research
          </button>
        )}
      </div>
    </form>
  );
}
