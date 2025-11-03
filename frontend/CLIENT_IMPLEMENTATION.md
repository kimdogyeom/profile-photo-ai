# 웹 클라이언트 구현 가이드

## 개요
이 문서는 ProfilePhotoAI 웹 클라이언트에서 구현해야 할 기능들을 정리합니다.

---

## 1. 스타일 프롬프트 관리

### 역할
사용자가 선택할 수 있는 프로필 사진 스타일을 클라이언트에서 관리하고, 백엔드에 전송할 프롬프트를 생성합니다.

### 구현 내용

#### 1.1 스타일 옵션 정의
```javascript
// constants/styles.js 또는 config/prompts.js

export const STYLE_PROMPTS = {
  professional: {
    id: 'professional',
    name: '전문적인',
    description: '깔끔한 배경과 비즈니스 정장으로 전문적인 프로필 사진',
    prompt: 'Create a professional business profile photo with a clean background, good lighting, and formal attire.',
    icon: '💼',
    preview: '/images/style-preview/professional.jpg'
  },
  casual: {
    id: 'casual',
    name: '캐주얼',
    description: '자연스러운 조명과 편안한 분위기의 프로필 사진',
    prompt: 'Create a casual, friendly profile photo with natural lighting and relaxed appearance.',
    icon: '😊',
    preview: '/images/style-preview/casual.jpg'
  },
  creative: {
    id: 'creative',
    name: '크리에이티브',
    description: '독특한 스타일링과 흥미로운 배경의 예술적인 프로필 사진',
    prompt: 'Create an artistic and creative profile photo with unique styling and interesting background.',
    icon: '🎨',
    preview: '/images/style-preview/creative.jpg'
  },
  minimal: {
    id: 'minimal',
    name: '미니멀',
    description: '단순한 배경과 깔끔한 미학의 미니멀한 프로필 사진',
    prompt: 'Create a minimalist profile photo with simple background and clean aesthetic.',
    icon: '⚪',
    preview: '/images/style-preview/minimal.jpg'
  },
  custom: {
    id: 'custom',
    name: '커스텀',
    description: '직접 프롬프트를 입력하여 원하는 스타일 생성',
    prompt: '',
    icon: '✏️',
    preview: '/images/style-preview/custom.jpg'
  }
};

export const getStylesList = () => Object.values(STYLE_PROMPTS);

export const getStylePrompt = (styleId, customPrompt = '') => {
  const style = STYLE_PROMPTS[styleId];
  if (!style) {
    return STYLE_PROMPTS.professional.prompt; // 기본값
  }
  
  if (styleId === 'custom') {
    return customPrompt || STYLE_PROMPTS.professional.prompt;
  }
  
  return style.prompt;
};
```

#### 1.2 스타일 선택 UI 컴포넌트
```jsx
// components/StyleSelector.jsx

import React, { useState } from 'react';
import { getStylesList, getStylePrompt } from '../config/prompts';

export const StyleSelector = ({ onStyleChange, selectedStyle }) => {
  const [customPrompt, setCustomPrompt] = useState('');
  const styles = getStylesList();

  const handleStyleSelect = (styleId) => {
    const prompt = getStylePrompt(styleId, customPrompt);
    onStyleChange({ styleId, prompt });
  };

  const handleCustomPromptChange = (text) => {
    setCustomPrompt(text);
    if (selectedStyle === 'custom') {
      const prompt = getStylePrompt('custom', text);
      onStyleChange({ styleId: 'custom', prompt });
    }
  };

  return (
    <div className="style-selector">
      <h3>스타일 선택</h3>
      
      {/* 프리셋 스타일 그리드 */}
      <div className="style-grid">
        {styles.map((style) => (
          <div
            key={style.id}
            className={`style-card ${selectedStyle === style.id ? 'selected' : ''}`}
            onClick={() => handleStyleSelect(style.id)}
          >
            <div className="style-icon">{style.icon}</div>
            <div className="style-name">{style.name}</div>
            <div className="style-description">{style.description}</div>
            {style.preview && (
              <img src={style.preview} alt={style.name} className="style-preview" />
            )}
          </div>
        ))}
      </div>

      {/* 커스텀 프롬프트 입력 */}
      {selectedStyle === 'custom' && (
        <div className="custom-prompt-input">
          <label htmlFor="custom-prompt">커스텀 프롬프트</label>
          <textarea
            id="custom-prompt"
            value={customPrompt}
            onChange={(e) => handleCustomPromptChange(e.target.value)}
            placeholder="원하는 프로필 사진 스타일을 자세히 설명해주세요..."
            maxLength={2000}
            rows={5}
          />
          <div className="character-count">
            {customPrompt.length} / 2000
          </div>
        </div>
      )}

      {/* 선택된 스타일 프롬프트 미리보기 (디버그용, 선택적) */}
      {process.env.NODE_ENV === 'development' && (
        <div className="prompt-preview">
          <strong>전송될 프롬프트:</strong>
          <pre>{getStylePrompt(selectedStyle, customPrompt)}</pre>
        </div>
      )}
    </div>
  );
};
```

#### 1.3 메인 이미지 생성 플로우
```jsx
// pages/GeneratePage.jsx

import React, { useState } from 'react';
import { StyleSelector } from '../components/StyleSelector';
import { uploadImage, generateImage } from '../services/api';

export const GeneratePage = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedStyle, setSelectedStyle] = useState('professional');
  const [generatedPrompt, setGeneratedPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [jobId, setJobId] = useState(null);

  const handleStyleChange = ({ styleId, prompt }) => {
    setSelectedStyle(styleId);
    setGeneratedPrompt(prompt);
  };

  const handleFileSelect = (file) => {
    setSelectedFile(file);
  };

  const handleGenerate = async () => {
    if (!selectedFile || !generatedPrompt) {
      alert('이미지와 스타일을 선택해주세요.');
      return;
    }

    setIsLoading(true);

    try {
      // 1. Presigned URL 획득
      const { uploadUrl, fileKey } = await uploadImage(selectedFile);

      // 2. S3에 직접 업로드
      await fetch(uploadUrl, {
        method: 'PUT',
        body: selectedFile,
        headers: {
          'Content-Type': selectedFile.type
        }
      });

      // 3. 이미지 생성 요청
      const response = await generateImage({
        fileKey: fileKey,
        prompt: generatedPrompt  // 클라이언트에서 생성한 프롬프트 전송
      });

      setJobId(response.jobId);
      
      // 4. WebSocket 연결 또는 폴링으로 결과 대기
      // (별도 구현)

    } catch (error) {
      console.error('Image generation failed:', error);
      alert('이미지 생성 요청에 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="generate-page">
      <h1>프로필 사진 생성</h1>
      
      {/* 이미지 업로드 */}
      <ImageUploader onFileSelect={handleFileSelect} />
      
      {/* 스타일 선택 */}
      <StyleSelector
        selectedStyle={selectedStyle}
        onStyleChange={handleStyleChange}
      />
      
      {/* 생성 버튼 */}
      <button
        onClick={handleGenerate}
        disabled={!selectedFile || !generatedPrompt || isLoading}
        className="generate-button"
      >
        {isLoading ? '생성 중...' : '프로필 사진 생성'}
      </button>
      
      {/* 결과 표시 */}
      {jobId && <JobStatus jobId={jobId} />}
    </div>
  );
};
```

---

## 2. API 서비스 레이어

### 2.1 API 클라이언트 구현
```javascript
// services/api.js

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;

// Cognito 토큰 가져오기 (Auth 라이브러리에 따라 다름)
const getAuthToken = async () => {
  // AWS Amplify 사용 예시
  const session = await Auth.currentSession();
  return session.getIdToken().getJwtToken();
};

// API 클라이언트 생성
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 요청 인터셉터: 인증 토큰 자동 추가
apiClient.interceptors.request.use(async (config) => {
  const token = await getAuthToken();
  config.headers.Authorization = `Bearer ${token}`;
  return config;
});

/**
 * 파일 업로드를 위한 Presigned URL 획득
 */
export const getUploadUrl = async (file) => {
  const response = await apiClient.post('/upload', {
    fileName: file.name,
    fileSize: file.size,
    contentType: file.type
  });
  
  return {
    uploadUrl: response.data.uploadUrl,
    fileKey: response.data.fileKey,
    expiresIn: response.data.expiresIn
  };
};

/**
 * S3에 파일 직접 업로드
 */
export const uploadToS3 = async (uploadUrl, file) => {
  await fetch(uploadUrl, {
    method: 'PUT',
    body: file,
    headers: {
      'Content-Type': file.type
    }
  });
};

/**
 * 이미지 생성 요청
 */
export const generateImage = async ({ fileKey, prompt }) => {
  const response = await apiClient.post('/generate', {
    fileKey,
    prompt  // 클라이언트에서 생성한 프롬프트
  });
  
  return {
    jobId: response.data.jobId,
    status: response.data.status,
    remainingQuota: response.data.remainingQuota
  };
};

/**
 * 편의 함수: 업로드와 URL 획득을 한 번에
 */
export const uploadImage = async (file) => {
  const { uploadUrl, fileKey } = await getUploadUrl(file);
  await uploadToS3(uploadUrl, file);
  return { fileKey };
};

/**
 * Job 상태 조회
 */
export const getJobStatus = async (jobId) => {
  const response = await apiClient.get(`/jobs/${jobId}`);
  return response.data;
};

/**
 * 사용자 정보 및 사용량 조회
 */
export const getUserInfo = async () => {
  const response = await apiClient.get('/user/me');
  return response.data;
};
```

---

## 3. 사용량 표시 UI

### 3.1 사용량 표시 컴포넌트
```jsx
// components/UsageQuota.jsx

import React, { useEffect, useState } from 'react';
import { getUserInfo } from '../services/api';

export const UsageQuota = () => {
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUsage();
  }, []);

  const fetchUsage = async () => {
    try {
      const data = await getUserInfo();
      setUsage({
        remaining: data.remainingQuota,
        limit: data.dailyLimit,
        used: data.dailyLimit - data.remainingQuota
      });
    } catch (error) {
      console.error('Failed to fetch usage:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;

  const percentage = (usage.used / usage.limit) * 100;

  return (
    <div className="usage-quota">
      <div className="usage-header">
        <span>오늘의 사용량</span>
        <span className="usage-count">
          {usage.used} / {usage.limit}
        </span>
      </div>
      
      <div className="usage-bar">
        <div
          className="usage-fill"
          style={{ width: `${percentage}%` }}
        />
      </div>
      
      <div className="usage-remaining">
        {usage.remaining > 0 ? (
          <span>남은 생성 횟수: {usage.remaining}회</span>
        ) : (
          <span className="usage-exceeded">
            오늘의 사용량을 모두 소진했습니다. 내일 다시 시도해주세요.
          </span>
        )}
      </div>
    </div>
  );
};
```

---

## 4. 실시간 알림 (WebSocket)

### 4.1 WebSocket 연결 관리
```javascript
// services/websocket.js

class WebSocketService {
  constructor() {
    this.ws = null;
    this.listeners = {};
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  async connect() {
    const token = await getAuthToken();
    const wsUrl = `${process.env.REACT_APP_WS_URL}?token=${token}`;
    
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.attemptReconnect();
    };
  }

  handleMessage(data) {
    const { type } = data;
    if (this.listeners[type]) {
      this.listeners[type].forEach(callback => callback(data));
    }
  }

  on(eventType, callback) {
    if (!this.listeners[eventType]) {
      this.listeners[eventType] = [];
    }
    this.listeners[eventType].push(callback);
  }

  off(eventType, callback) {
    if (this.listeners[eventType]) {
      this.listeners[eventType] = this.listeners[eventType].filter(
        cb => cb !== callback
      );
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        this.connect();
      }, 2000 * this.reconnectAttempts);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export const wsService = new WebSocketService();
```

### 4.2 WebSocket 이벤트 처리
```jsx
// components/JobStatus.jsx

import React, { useEffect, useState } from 'react';
import { wsService } from '../services/websocket';
import { getJobStatus } from '../services/api';

export const JobStatus = ({ jobId }) => {
  const [status, setStatus] = useState('pending');
  const [imageUrl, setImageUrl] = useState(null);
  const [error, setError] = useState(null);
  const [processingTime, setProcessingTime] = useState(null);

  useEffect(() => {
    // WebSocket 연결
    wsService.connect();

    // 완료 이벤트 리스너
    const handleComplete = (data) => {
      if (data.jobId === jobId) {
        setStatus('completed');
        setImageUrl(data.imageUrl);
        setProcessingTime(data.processingTime);
      }
    };

    // 실패 이벤트 리스너
    const handleFailed = (data) => {
      if (data.jobId === jobId) {
        setStatus('failed');
        setError(data.error);
      }
    };

    wsService.on('image_completed', handleComplete);
    wsService.on('image_failed', handleFailed);

    // 폴백: 주기적으로 상태 확인 (WebSocket 연결 실패 대비)
    const pollInterval = setInterval(async () => {
      try {
        const jobData = await getJobStatus(jobId);
        setStatus(jobData.status);
        if (jobData.status === 'completed') {
          setImageUrl(jobData.outputImageUrl);
          clearInterval(pollInterval);
        } else if (jobData.status === 'failed') {
          setError(jobData.error);
          clearInterval(pollInterval);
        }
      } catch (err) {
        console.error('Failed to poll job status:', err);
      }
    }, 5000);

    return () => {
      wsService.off('image_completed', handleComplete);
      wsService.off('image_failed', handleFailed);
      clearInterval(pollInterval);
    };
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
        <img src={imageUrl} alt="Generated profile" />
        <p>처리 시간: {processingTime?.toFixed(2)}초</p>
        <button onClick={() => window.open(imageUrl)}>
          다운로드
        </button>
      </div>
    );
  }

  if (status === 'failed') {
    return (
      <div className="job-status-failed">
        <h3>생성 실패</h3>
        <p>{error || '알 수 없는 오류가 발생했습니다.'}</p>
        <button onClick={() => window.location.reload()}>
          다시 시도
        </button>
      </div>
    );
  }

  return null;
};
```

---

## 5. 에러 처리

### 5.1 전역 에러 핸들러
```javascript
// utils/errorHandler.js

export const handleApiError = (error) => {
  if (error.response) {
    const { status, data } = error.response;
    
    switch (status) {
      case 400:
        return {
          title: '잘못된 요청',
          message: data.error || '요청 형식이 올바르지 않습니다.'
        };
      
      case 401:
        return {
          title: '인증 필요',
          message: '로그인이 필요합니다.',
          action: 'redirect-login'
        };
      
      case 404:
        return {
          title: '파일을 찾을 수 없음',
          message: '업로드한 파일을 찾을 수 없습니다. 다시 업로드해주세요.'
        };
      
      case 429:
        return {
          title: '사용량 초과',
          message: data.message || '일일 사용량을 초과했습니다. 내일 다시 시도해주세요.',
          remainingQuota: data.remainingQuota
        };
      
      case 500:
        return {
          title: '서버 오류',
          message: '서버에서 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'
        };
      
      default:
        return {
          title: '오류',
          message: data.error || '알 수 없는 오류가 발생했습니다.'
        };
    }
  }
  
  return {
    title: '네트워크 오류',
    message: '네트워크 연결을 확인해주세요.'
  };
};
```

### 5.2 에러 표시 컴포넌트
```jsx
// components/ErrorAlert.jsx

import React from 'react';

export const ErrorAlert = ({ error, onClose }) => {
  if (!error) return null;

  return (
    <div className="error-alert">
      <div className="error-header">
        <h4>{error.title}</h4>
        <button onClick={onClose}>×</button>
      </div>
      <p>{error.message}</p>
      {error.remainingQuota !== undefined && (
        <p className="remaining-quota">
          남은 사용량: {error.remainingQuota}회
        </p>
      )}
    </div>
  );
};
```

---

## 6. 구현 체크리스트

### 필수 기능
- [ ] 스타일 프롬프트 상수 정의 (professional, casual, creative, minimal, custom)
- [ ] 스타일 선택 UI 컴포넌트
- [ ] 커스텀 프롬프트 입력 필드 (2000자 제한)
- [ ] API 서비스 레이어 (uploadImage, generateImage)
- [ ] 파일 업로드 플로우 (Presigned URL → S3 직접 업로드 → 생성 요청)
- [ ] 사용량 표시 UI
- [ ] Job 상태 추적 (pending → processing → completed/failed)
- [ ] 에러 처리 (400, 401, 404, 429, 500)
- [ ] 결과 이미지 표시 및 다운로드

### 선택 기능
- [ ] WebSocket 실시간 알림
- [ ] Job 상태 폴링 (WebSocket 대체)
- [ ] 스타일 프리뷰 이미지
- [ ] 생성 이력 페이지
- [ ] 다크 모드
- [ ] 반응형 디자인
- [ ] 로딩 애니메이션
- [ ] 이미지 미리보기

### 보안 및 성능
- [ ] Cognito 토큰 자동 갱신
- [ ] API 요청 재시도 로직
- [ ] 파일 크기/타입 검증 (10MB, jpg/jpeg/png/webp)
- [ ] 업로드 진행률 표시
- [ ] 이미지 캐싱
- [ ] 오류 로깅 (Sentry 등)

---

## 7. 환경 변수 설정

```env
# .env.local 또는 .env.production

REACT_APP_API_BASE_URL=https://api.profilephotoai.com
REACT_APP_WS_URL=wss://ws.profilephotoai.com
REACT_APP_COGNITO_USER_POOL_ID=ap-northeast-2_xxxxxxxxx
REACT_APP_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
REACT_APP_REGION=ap-northeast-2
```

---

## 8. 디자인 가이드라인

### 스타일 카드 레이아웃
- 그리드 형식 (2열 또는 3열)
- 각 카드에 아이콘, 이름, 설명, 프리뷰 이미지
- 선택된 카드는 하이라이트 (border, shadow)
- 호버 효과

### 색상 팔레트 (예시)
- Primary: #4A90E2 (파란색)
- Success: #7ED321 (초록색)
- Error: #D0021B (빨간색)
- Warning: #F5A623 (주황색)
- Background: #F8F9FA
- Text: #333333

### 타이포그래피
- Heading: 'Pretendard', sans-serif
- Body: 'Pretendard', sans-serif
- 크기: 제목 24px, 본문 16px, 설명 14px

---

## 참고 사항

1. **프롬프트 품질**: 사용자에게 효과적인 프롬프트 작성법 가이드 제공
2. **UX**: 스타일 선택 시 예상 결과 이미지 표시하여 사용자 이해도 향상
3. **성능**: 이미지 업로드는 S3 직접 업로드로 Lambda 우회하여 비용 절감
4. **에러 처리**: 사용자 친화적인 에러 메시지 제공
5. **접근성**: 키보드 네비게이션, 스크린 리더 지원
