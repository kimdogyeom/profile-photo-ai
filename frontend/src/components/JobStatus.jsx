import React, { useEffect, useState } from 'react';
import { getJobStatus, getDownloadUrl } from '../services/api';
import './JobStatus.css';

export const JobStatus = ({ jobId }) => {
  const [status, setStatus] = useState('pending');
  const [imageUrl, setImageUrl] = useState(null);
  const [error, setError] = useState(null);
  const [processingTime, setProcessingTime] = useState(null);
  const [loading, setLoading] = useState(false);

  // Job 완료 후 다운로드 URL 가져오기
  const fetchDownloadUrl = async (jobId) => {
    try {
      setLoading(true);
      const downloadUrl = await getDownloadUrl(jobId);
      setImageUrl(downloadUrl);
    } catch (err) {
      console.error('Failed to get download URL:', err);
      setError('이미지를 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!jobId) return;

    // Poll job status every 3 seconds
    const pollInterval = setInterval(async () => {
      try {
        const jobData = await getJobStatus(jobId);
        setStatus(jobData.status);
        
        if (jobData.status === 'completed') {
          setProcessingTime(jobData.processingTime);
          clearInterval(pollInterval);
          // Job 완료 시 다운로드 URL 가져오기
          await fetchDownloadUrl(jobId);
        } else if (jobData.status === 'failed') {
          setError(jobData.error);
          clearInterval(pollInterval);
        }
      } catch (err) {
        console.error('Failed to poll job status:', err);
        setError('작업 상태를 확인할 수 없습니다.');
        clearInterval(pollInterval);
      }
    }, 3000);

    return () => clearInterval(pollInterval);
  }, [jobId]);

  if (status === 'pending' || status === 'queued' || status === 'processing') {
    return (
      <div className="job-status-loading">
        <div className="spinner" />
        <p>이미지를 생성하는 중입니다...</p>
        <p className="status-text">상태: {status}</p>
      </div>
    );
  }

  if (status === 'completed') {
    return (
      <div className="job-status-completed">
        <h3>생성 완료!</h3>
        {loading ? (
          <div className="spinner-small">이미지 로딩 중...</div>
        ) : imageUrl ? (
          <>
            <div className="result-image-container">
              <img src={imageUrl} alt="Generated profile" className="result-image" />
            </div>
            {processingTime && (
              <p className="processing-time">처리 시간: {processingTime.toFixed(2)}초</p>
            )}
            <div className="result-actions">
              <button 
                onClick={() => window.open(imageUrl, '_blank')}
                className="download-button"
              >
                다운로드
              </button>
              <button 
                onClick={() => window.location.reload()}
                className="new-generation-button"
              >
                새로 생성하기
              </button>
            </div>
          </>
        ) : (
          <p className="error-message">이미지를 불러올 수 없습니다.</p>
        )}
      </div>
    );
  }

  if (status === 'failed') {
    return (
      <div className="job-status-failed">
        <h3>생성 실패</h3>
        <p className="error-message">{error || '알 수 없는 오류가 발생했습니다.'}</p>
        <button 
          onClick={() => window.location.reload()}
          className="retry-button"
        >
          다시 시도
        </button>
      </div>
    );
  }

  return null;
};
