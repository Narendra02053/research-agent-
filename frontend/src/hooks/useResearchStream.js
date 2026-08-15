import { useState, useEffect, useCallback, useRef } from 'react';
import { researchApi } from '../api/client';

export function useResearchStream() {
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, pending, running, completed, failed
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [events, setEvents] = useState([]);
  
  const wsRef = useRef(null);

  const connectWebSocket = useCallback((id) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    // Determine WS protocol based on current location protocol
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // When using Vite proxy, we can connect to the current host
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/research/${id}`;
    
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setEvents(prev => [...prev, data]);
        
        switch (data.event_type) {
          case 'workflow_started':
            setStatus('running');
            break;
          case 'progress_update':
          case 'planner_started':
          case 'search_started':
          case 'retrieval_started':
          case 'analysis_started':
          case 'report_started':
          case 'evaluation_started':
            if (data.data?.step) setCurrentStep(data.data.step);
            if (data.data?.progress) setProgress(data.data.progress);
            break;
          case 'workflow_finished':
            setStatus('completed');
            setProgress(100);
            setCurrentStep('done');
            if (data.data) {
              setResult({
                report: data.data.report,
                sources: data.data.sources,
                quality_metrics: data.data.metrics
              });
            }
            break;
          case 'workflow_failed':
            setStatus('failed');
            setError(data.data?.error || 'Research failed');
            break;
        }
      } catch (e) {
        console.error("Failed to parse websocket message", e);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    wsRef.current = ws;
  }, []);

  const submitQuery = async (query) => {
    try {
      setStatus('pending');
      setError(null);
      setResult(null);
      setProgress(0);
      setEvents([]);
      
      const data = await researchApi.submitJob(query);
      setJobId(data.job_id);
      connectWebSocket(data.job_id);
    } catch (err) {
      setStatus('failed');
      setError(err.response?.data?.detail || 'Failed to submit research query');
    }
  };

  const cancelJob = async () => {
    if (jobId && status === 'running') {
      try {
        await researchApi.cancelJob(jobId);
        setStatus('failed');
        setError('Job was cancelled by the user.');
        if (wsRef.current) wsRef.current.close();
      } catch (err) {
        console.error('Failed to cancel job:', err);
      }
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    jobId,
    status,
    progress,
    currentStep,
    result,
    error,
    events,
    submitQuery,
    cancelJob,
    reset: () => {
      setJobId(null);
      setStatus('idle');
      setResult(null);
      setError(null);
      setEvents([]);
      if (wsRef.current) wsRef.current.close();
    }
  };
}
