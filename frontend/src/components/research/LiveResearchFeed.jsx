import { useEffect, useRef } from 'react';
import { Terminal } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function LiveResearchFeed({ events }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden mt-8 max-w-4xl mx-auto shadow-lg">
      {/* Terminal-style header */}
      <div className="bg-slate-800 px-4 py-3 border-b border-slate-700 flex items-center gap-3">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-rose-500" />
          <div className="w-3 h-3 rounded-full bg-amber-400" />
          <div className="w-3 h-3 rounded-full bg-emerald-500" />
        </div>
        <div className="flex items-center gap-2 ml-2">
          <Terminal size={14} className="text-slate-400" />
          <h4 className="text-xs font-mono text-slate-400 uppercase tracking-widest">
            Live Event Stream
          </h4>
        </div>
      </div>

      <div
        ref={scrollRef}
        className="p-4 h-64 overflow-y-auto font-mono text-sm space-y-2 scroll-smooth"
      >
        <AnimatePresence>
          {events.length === 0 && (
            <div className="text-slate-500 italic text-xs">
              {'>'} Waiting for connection...
            </div>
          )}
          {events.map((evt, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-start gap-3"
            >
              <span className="text-slate-500 shrink-0 text-xs">
                [{new Date(evt.timestamp * 1000).toLocaleTimeString()}]
              </span>
              <span className="text-orange-400 font-bold text-xs shrink-0">
                {evt.event_type}
              </span>
              <span className="text-slate-300 text-xs truncate">
                {JSON.stringify(evt.data)}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
