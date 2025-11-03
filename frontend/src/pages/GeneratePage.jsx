import React, { useState } from 'react';
import { StyleSelector } from '../components/StyleSelector';
import { ImageUploader } from '../components/ImageUploader';
import { UsageQuota } from '../components/UsageQuota';
import { JobStatus } from '../components/JobStatus';
import { uploadImage, generateImage } from '../services/api';
import './GeneratePage.css';

export const GeneratePage = ({ onLogout, userInfo }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedStyle, setSelectedStyle] = useState('professional');
  const [generatedPrompt, setGeneratedPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [jobId, setJobId] = useState(null);
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
        prompt: generatedPrompt
      });

      setJobId(response.jobId);
      
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

  const canGenerate = selectedFile && generatedPrompt && !isLoading && !jobId;

  return (
    <div className="generate-page">
      <header className="page-header">
        <div>
          <h1>ProfilePhotoAI</h1>
          <p>AI로 완벽한 프로필 사진을 만들어보세요</p>
        </div>
        <div className="user-section">
          {userInfo && (
            <span className="user-email">{userInfo.email}</span>
          )}
          <button onClick={onLogout} className="logout-button">
            로그아웃
          </button>
        </div>
      </header>

      <div className="page-content">
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
          
          {jobId && <JobStatus jobId={jobId} />}
        </div>

        <div className="sidebar">
          <div className="tips-section">
            <h3>💡 더 좋은 결과를 위한 팁</h3>
            <ul>
              <li>얼굴이 선명하게 보이는 사진을 사용하세요</li>
              <li>조명이 밝고 균일한 사진이 좋습니다</li>
              <li>정면을 바라보는 사진을 권장합니다</li>
              <li>배경이 복잡하지 않은 사진이 효과적입니다</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
