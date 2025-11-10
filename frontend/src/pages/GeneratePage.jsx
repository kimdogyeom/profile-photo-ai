import React, { useState } from 'react';
import { StyleSelector } from '../components/StyleSelector';
import { ImageUploader } from '../components/ImageUploader';
import { UsageQuota } from '../components/UsageQuota';
import { JobHistoryList } from '../components/JobHistoryList';
import { Logo } from '../components/Logo';
import { LogOutIcon } from '../components/Icons';
import { uploadImage, generateImage } from '../services/api';
import './GeneratePage.css';

export const GeneratePage = ({ onLogout, userInfo }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedStyle, setSelectedStyle] = useState('professional');
  const [generatedPrompt, setGeneratedPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [pendingJobs, setPendingJobs] = useState([]);
  const [error, setError] = useState(null);

  const handleStyleChange = ({ styleId, prompt }) => {
    setSelectedStyle(styleId);
    setGeneratedPrompt(prompt);
  };

  const handleFileSelect = (file) => {
    setSelectedFile(file);
    setError(null);
  };

  const handleGenerate = async () => {
    if (!selectedFile || !generatedPrompt) {
      setError('이미지와 스타일을 선택해주세요.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Upload image to S3
      const { fileKey } = await uploadImage(selectedFile);

      // Request image generation
      const response = await generateImage({
        fileKey: fileKey,
        prompt: generatedPrompt,
        style: selectedStyle  // 선택한 스타일 전달
      });

      // Create pending job with preview
      const inputImageUrl = URL.createObjectURL(selectedFile);
      const newPendingJob = {
        jobId: response.jobId,
        status: 'pending',
        style: selectedStyle,
        inputImage: inputImageUrl,
        outputImageUrl: null,
        createdAt: new Date().toISOString(),
        prompt: generatedPrompt
      };

      setPendingJobs(prev => [newPendingJob, ...prev]);
      
      // Keep the selected file for potential retry
      // setSelectedFile(null); // Removed to persist input image
      
    } catch (error) {
      console.error('Image generation failed:', error);
      
      if (error.response?.status === 429) {
        setError('일일 사용량을 초과했습니다. 내일 다시 시도해주세요.');
      } else if (error.response?.status === 404) {
        setError('업로드한 파일을 찾을 수 없습니다. 다시 업로드해주세요.');
      } else {
        setError('이미지 생성 요청에 실패했습니다. 잠시 후 다시 시도해주세요.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleJobComplete = (completedJob) => {
    setPendingJobs(prev => prev.filter(job => job.jobId !== completedJob.jobId));
  };

  const canGenerate = selectedFile && generatedPrompt && !isLoading;

  return (
    <div className="generate-page">
      <header className="page-header">
        <div>
          <Logo size="large" variant="full" />
          <p>AI로 완벽한 프로필 사진을 만들어보세요</p>
        </div>
        <div className="user-section">
          {userInfo && (
            <span className="user-email">{userInfo.email}</span>
          )}
          <button onClick={onLogout} className="logout-button">
            <LogOutIcon size={16} color="currentColor" style={{ marginRight: '6px' }} />
            로그아웃
          </button>
        </div>
      </header>

      <div className="page-content">
        <div className="history-section">
          <JobHistoryList 
            pendingJobs={pendingJobs}
            onJobComplete={handleJobComplete}
          />
        </div>

        <div className="main-section">
          <UsageQuota />
          
          <ImageUploader 
            onFileSelect={handleFileSelect}
            selectedFile={selectedFile}
          />
          
          <StyleSelector
            selectedStyle={selectedStyle}
            onStyleChange={handleStyleChange}
          />

          {error && (
            <div className="error-alert">
              <p>{error}</p>
              <button onClick={() => setError(null)}>×</button>
            </div>
          )}
          
          <div className="generate-section">
            <button
              onClick={handleGenerate}
              disabled={!canGenerate}
              className={`generate-button ${!canGenerate ? 'disabled' : ''}`}
            >
              {isLoading ? '업로드 중...' : '프로필 사진 생성'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
