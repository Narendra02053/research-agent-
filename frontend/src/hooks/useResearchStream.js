// useResearchStream.js - Custom hook for managing WebSocket research streams.
import { useState, useEffect, useCallback, useRef } from 'react';
import { researchApi } from '../api/client';

const POLL_INTERVAL_MS = 1000;
const JOB_TIMEOUT_MS = 6 * 60 * 1000;

export function useResearchStream() {
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState('idle');
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [events, setEvents] = useState([]);

  const wsRef = useRef(null);
  const statusRef = useRef(status);
  statusRef.current = status;

  const applyCompleted = useCallback((res) => {
    setStatus('completed');
    setProgress(100);
    setCurrentStep('done');
    setResult({
      report: res.report,
      sources: res.sources || [],
      quality_metrics: res.quality_metrics || {},
    });
  }, []);

  const connectWebSocket = useCallback((id) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const API_URL = import.meta.env.VITE_API_URL || '';
    let wsUrl;
    if (API_URL) {
      const wsProtocol = API_URL.startsWith('https') ? 'wss:' : 'ws:';
      const host = API_URL.replace(/^https?:\/\//, '');
      wsUrl = `${wsProtocol}//${host}/api/v1/ws/research/${id}`;
    } else {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${protocol}//${window.location.host}/api/v1/ws/research/${id}`;
    }
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setEvents((prev) => [...prev, data]);

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
            if (data.data?.progress != null) setProgress(data.data.progress);
            setStatus('running');
            break;
          case 'workflow_finished':
            applyCompleted({
              report: data.data?.report,
              sources: data.data?.sources,
              quality_metrics: data.data?.metrics,
            });
            break;
          case 'workflow_failed':
            setStatus('failed');
            setError(data.data?.error || 'Research failed');
            break;
          default:
            break;
        }
      } catch (e) {
        console.error('Failed to parse websocket message', e);
      }
    };

    ws.onerror = () => {
      console.warn('WebSocket connection failed — falling back to HTTP polling');
    };

    wsRef.current = ws;
  }, [applyCompleted]);

  const pollStatus = useCallback(async () => {
    if (!jobId || statusRef.current === 'completed' || statusRef.current === 'failed') {
      return;
    }

    try {
      const data = await researchApi.checkStatus(jobId);
      setProgress(data.progress ?? 0);
      setCurrentStep(data.current_step ?? '');

      if (data.status === 'running' || (data.status === 'pending' && data.progress > 0)) {
        setStatus('running');
      }

      if (data.status === 'completed') {
        const res = await researchApi.getResult(jobId);
        applyCompleted(res);
      } else if (data.status === 'failed' || data.status === 'cancelled') {
        setStatus('failed');
        setError(data.error || 'Research job failed during execution.');
      }
    } catch (err) {
      console.error('Error polling status:', err);
    }
  }, [jobId, applyCompleted]);

  useEffect(() => {
    if (!jobId || status === 'completed' || status === 'failed' || status === 'idle') {
      return undefined;
    }

    pollStatus();
    const intervalId = setInterval(pollStatus, POLL_INTERVAL_MS);
    return () => clearInterval(intervalId);
  }, [jobId, status, pollStatus]);

  useEffect(() => {
    if (status !== 'running' && status !== 'pending') {
      return undefined;
    }

    const timeoutId = setTimeout(() => {
      setStatus('failed');
      setError(
        'Research timed out after 6 minutes. Check that GROQ_API_KEY and TAVILY_API_KEY are set in backend/.env'
      );
    }, JOB_TIMEOUT_MS);

    return () => clearTimeout(timeoutId);
  }, [status, jobId]);

  const submitQuery = async (query) => {
    try {
      setStatus('pending');
      setError(null);
      setResult(null);
      setProgress(0);
      setCurrentStep('');
      setEvents([]);

      const data = await researchApi.submitJob(query);
      setJobId(data.job_id);
      setStatus('running');
      connectWebSocket(data.job_id);
    } catch (err) {
      setStatus('failed');
      setError(err.response?.data?.detail || 'Failed to submit research query');
    }
  };

  const cancelJob = async () => {
    if (jobId && (status === 'running' || status === 'pending')) {
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
    },
  };
}
