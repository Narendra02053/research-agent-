import { useState, useEffect, useCallback } from 'react';
import { researchApi } from '../api/client';

export function useResearch() {
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, pending, running, completed, failed
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const submitQuery = async (query) => {
    try {
      setStatus('pending');
      setError(null);
      setResult(null);
      setProgress(0);
      
      const data = await researchApi.submitJob(query);
      setJobId(data.job_id);
      setStatus('running');
    } catch (err) {
      setStatus('failed');
      setError(err.response?.data?.detail || 'Failed to submit research query');
    }
  };

  const pollStatus = useCallback(async () => {
    if (!jobId || status === 'completed' || status === 'failed') return;

    try {
      const data = await researchApi.checkStatus(jobId);
      setProgress(data.progress);
      setCurrentStep(data.current_step);
      
      if (data.status === 'completed' || data.status === 'failed') {
        setStatus(data.status);
        if (data.status === 'completed') {
          const res = await researchApi.getResult(jobId);
          setResult(res);
        } else {
          setError('Research job failed during execution.');
        }
      }
    } catch (err) {
      console.error('Error polling status:', err);
      // Don't fail immediately on a single poll error
    }
  }, [jobId, status]);

  useEffect(() => {
    let intervalId;
    if (status === 'running') {
      intervalId = setInterval(pollStatus, 2000); // Poll every 2 seconds
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [status, pollStatus]);

  const cancelJob = async () => {
    if (jobId && status === 'running') {
      try {
        await researchApi.cancelJob(jobId);
        setStatus('failed');
        setError('Job was cancelled by the user.');
      } catch (err) {
        console.error('Failed to cancel job:', err);
      }
    }
  };

  return {
    jobId,
    status,
    progress,
    currentStep,
    result,
    error,
    submitQuery,
    cancelJob,
    reset: () => {
      setJobId(null);
      setStatus('idle');
      setResult(null);
      setError(null);
    }
  };
}
