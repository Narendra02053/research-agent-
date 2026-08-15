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
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden mt-8 max-w-4xl mx-auto shadow-2xl">
      <div className="bg-gray-950 px-4 py-3 border-b border-gray-800 flex items-center gap-2">
        <Terminal size={16} className="text-gray-400" />
        <h4 className="text-xs font-mono text-gray-400 uppercase tracking-wider">Live Event Stream</h4>
      </div>
      <div 
        ref={scrollRef}
        className="p-4 h-64 overflow-y-auto font-mono text-sm space-y-2 scroll-smooth"
      >
        <AnimatePresence>
          {events.length === 0 && (
            <div className="text-gray-600 italic">Waiting for connection...</div>
          )}
          {events.map((evt, idx) => (
            <motion.div 
              key={idx}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-start gap-3"
            >
              <span className="text-gray-600 shrink-0">
                [{new Date(evt.timestamp * 1000).toLocaleTimeString()}]
              </span>
              <span className="text-blue-400 font-semibold">
                {evt.event_type}
              </span>
              <span className="text-gray-300">
                {JSON.stringify(evt.data)}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
