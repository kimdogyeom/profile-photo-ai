import React from 'react';
import './JobCard.css';

export const JobCard = ({ job, onRetry }) => {
  const { jobId, status, inputImage, outputImageUrl, style, createdAt, error } = job;
  
  const isLoading = ['pending', 'queued', 'processing'].includes(status);
  const isCompleted = status === 'completed';
  const isFailed = status === 'failed';
  
  const imageSrc = isCompleted ? outputImageUrl : inputImage;
  
  const getStatusText = () => {
    switch (status) {
      case 'pending': return 'AI 생성 준비 중...';
      case 'queued': return '대기열 등록 완료';
      case 'processing': return 'AI가 프로필 사진을 만들고 있어요';
      case 'completed': return '완료';
      case 'failed': return '생성 실패';
      default: return status;
    }
  };

  const formatStyle = (style) => {
    const styles = {
      professional: '프로페셔널',
      casual: '캐주얼',
      artistic: '아티스틱',
      vintage: '빈티지'
    };
    return styles[style] || style;
  };

  return (
    <div className={`job-card ${status}`}>
      <div className="job-card-image-wrapper">
        <img 
          src={imageSrc} 
          alt={formatStyle(style)}
          className={`job-card-image ${isLoading ? 'processing' : ''} ${isCompleted ? 'completed' : ''}`}
          loading="lazy"
        />
        
        {isLoading && (
          <div className="job-card-overlay">
            <div className="loading-container">
              <div className="loading-spinner"></div>
              <div className="loading-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
            <p className="status-text">{getStatusText()}</p>
            <div className="estimated-time">약 30~60초 소요</div>
          </div>
        )}
        
        {isFailed && (
          <div className="job-card-overlay error">
            <div className="error-icon">⚠️</div>
            <p className="error-text">{error || '이미지 생성에 실패했습니다'}</p>
            <button 
              className="retry-button"
              onClick={() => onRetry?.(job)}
            >
              다시 시도
            </button>
          </div>
        )}

        {isCompleted && (
          <div className="job-card-badge">✨ 완성</div>
        )}
      </div>
      
      <div className="job-card-info">
        <div className="job-card-meta">
          <span className="job-style">{formatStyle(style)}</span>
          <span className="job-date">
            {new Date(createdAt).toLocaleString('ko-KR', {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            })}
          </span>
        </div>
        
        {isCompleted && (
          <button className="download-button" onClick={() => window.open(outputImageUrl)}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M8 11L4 7h2.5V3h3v4H12L8 11z" fill="currentColor"/>
              <path d="M2 13h12v1H2v-1z" fill="currentColor"/>
            </svg>
            다운로드
          </button>
        )}
      </div>
    </div>
  );
};
