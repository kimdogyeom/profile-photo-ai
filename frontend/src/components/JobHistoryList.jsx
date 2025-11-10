import React, { useState, useEffect, useCallback } from 'react';
import { JobCard } from './JobCard';
import { getUserJobs, getJobStatus } from '../services/api';
import './JobHistoryList.css';

export const JobHistoryList = ({ pendingJobs = [], onJobComplete }) => {
  const [completedJobs, setCompletedJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchJobs = useCallback(async () => {
    try {
      const response = await getUserJobs(50);
      setCompletedJobs(response.jobs || []);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch jobs:', err);
      setError('이력을 불러오는데 실패했습니다');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  useEffect(() => {
    const pollingIntervals = new Map();

    pendingJobs.forEach(job => {
      if (!pollingIntervals.has(job.jobId)) {
        const pollJob = async () => {
          try {
            const status = await getJobStatus(job.jobId);
            
            if (status.status === 'completed') {
              clearInterval(pollingIntervals.get(job.jobId));
              pollingIntervals.delete(job.jobId);
              
              setCompletedJobs(prev => {
                const exists = prev.find(j => j.jobId === status.jobId);
                if (exists) return prev;
                return [status, ...prev];
              });
              
              onJobComplete?.(status);
            } else if (status.status === 'failed') {
              clearInterval(pollingIntervals.get(job.jobId));
              pollingIntervals.delete(job.jobId);
              onJobComplete?.(status);
            }
          } catch (err) {
            console.error('Polling error:', err);
          }
        };

        const interval = setInterval(pollJob, 3000);
        pollingIntervals.set(job.jobId, interval);

        setTimeout(() => {
          if (pollingIntervals.has(job.jobId)) {
            clearInterval(pollingIntervals.get(job.jobId));
            pollingIntervals.delete(job.jobId);
          }
        }, 300000);
      }
    });

    return () => {
      pollingIntervals.forEach(interval => clearInterval(interval));
      pollingIntervals.clear();
    };
  }, [pendingJobs, onJobComplete]);

  const allJobs = [...pendingJobs, ...completedJobs.filter(
    cj => !pendingJobs.find(pj => pj.jobId === cj.jobId)
  )];

  const handleRetry = async (job) => {
    console.log('Retry job:', job);
  };

  if (loading && allJobs.length === 0) {
    return (
      <div className="job-history-list">
        <div className="job-history-header">
          <h3 className="job-history-title">생성 이력</h3>
        </div>
        <div className="job-history-skeleton">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="skeleton-card">
              <div className="skeleton-image"></div>
              <div className="skeleton-content">
                <div className="skeleton-line"></div>
                <div className="skeleton-line short"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="job-history-list">
        <div className="job-history-header">
          <h3 className="job-history-title">생성 이력</h3>
        </div>
        <div className="job-history-error">
          <div className="error-icon">😢</div>
          <p>{error}</p>
          <button onClick={fetchJobs} className="retry-fetch-button">
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="job-history-list">
      <div className="job-history-header">
        <h3 className="job-history-title">
          생성 이력
          {allJobs.length > 0 && (
            <span className="job-count">{allJobs.length}</span>
          )}
        </h3>
        {allJobs.length > 0 && (
          <button onClick={fetchJobs} className="refresh-button" title="새로고침">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M23 4v6h-6M1 20v-6h6"/>
              <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
            </svg>
          </button>
        )}
      </div>
      
      {allJobs.length === 0 ? (
        <div className="job-history-empty">
          <div className="empty-illustration">
            <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
              <circle cx="60" cy="60" r="50" fill="#f3f4f6" opacity="0.5"/>
              <path d="M60 35v50M35 60h50" stroke="#9ca3af" strokeWidth="4" strokeLinecap="round"/>
            </svg>
          </div>
          <h4>아직 생성된 프로필 사진이 없어요</h4>
          <p>우측 메뉴에서 사진을 업로드하고<br/>원하는 스타일을 선택해보세요!</p>
        </div>
      ) : (
        <div className="job-grid">
          {allJobs.map(job => (
            <JobCard key={job.jobId} job={job} onRetry={handleRetry} />
          ))}
        </div>
      )}
    </div>
  );
};
