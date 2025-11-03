# 프론트엔드-백엔드 통합 가이드

## 현재 상태 점검

✅ **완료된 구현:**
- API 서비스 레이어 (`src/services/api.js`)
- 스타일 프롬프트 관리 (`src/config/prompts.js`)
- 메인 페이지 (`src/pages/GeneratePage.jsx`)
- 컴포넌트 (StyleSelector, JobStatus, ImageUploader, UsageQuota)

## 백엔드 API와의 동기화

### ✅ 잘 맞춰진 부분

1. **파일 업로드 플로우**
   - 프론트: `getUploadUrl()` → `uploadToS3()` 
   - 백엔드: `POST /upload` → Presigned URL 반환
   - ✅ 완벽히 일치

2. **이미지 생성 요청**
   - 프론트: `generateImage({ fileKey, prompt })`
   - 백엔드: `POST /generate` with `{ fileKey, prompt }`
   - ✅ 완벽히 일치 (style 제거됨)

3. **프롬프트 관리**
   - 프론트: 클라이언트에서 전체 프롬프트 생성
   - 백엔드: 프롬프트를 그대로 받아서 사용
   - ✅ 완벽히 일치

### ⚠️ 수정 필요한 부분

#### 1. Job 상태 조회 API 엔드포인트

**현재 프론트엔드 코드:**
```javascript
export const getJobStatus = async (jobId) => {
  const response = await apiClient.get(`/jobs/${jobId}`);
  return response.data;
};
```

**백엔드 구현 필요:**
- 현재 `template.yaml`에 `/jobs/{jobId}` GET 엔드포인트가 없음
- Lambda 함수 추가 또는 ApiManager에 라우팅 추가 필요

**해결 방안:**
1. ApiManager Lambda에 GET 메서드 추가
2. JobStatus 컴포넌트에서 폴링 대신 Mock 데이터 사용 (이미 구현됨)

#### 2. 사용자 정보 조회 API

**현재 프론트엔드 코드:**
```javascript
export const getUserInfo = async () => {
  const response = await apiClient.get('/user/me');
  return response.data;
};
```

**백엔드 구현 필요:**
- `/user/me` GET 엔드포인트 추가 필요

## 로컬 테스트 설정

### 1. 환경 변수 설정

```bash
cd frontend
cp .env.example .env
```

`.env` 파일 수정:
```bash
REACT_APP_API_BASE_URL=http://localhost:3001
```

### 2. SAM 로컬 API 서버 시작

```bash
# 프로젝트 루트에서
make start
# 또는
sam local start-api --port 3001 --env-vars .env
```

### 3. 프론트엔드 개발 서버 시작

```bash
cd frontend
npm install
npm start
```

### 4. 인증 없이 테스트

현재 백엔드 Lambda에서 Cognito 인증을 검증하므로, 로컬 테스트를 위해 다음 옵션 중 하나 선택:

**옵션 A: Mock 인증 (개발용)**
`api.js`에 이미 구현됨:
```javascript
const getAuthToken = async () => {
  return 'mock-jwt-token';
};
```

**옵션 B: 테스트 이벤트 사용**
SAM Local invoke로 직접 테스트:
```bash
sam local invoke ApiManagerFunction \
  --event tests/events/api-manager-event.json
```

**옵션 C: Cognito 통합**
실제 Cognito 토큰 사용 (프로덕션 준비):
```javascript
import { Auth } from 'aws-amplify';

const getAuthToken = async () => {
  const session = await Auth.currentSession();
  return session.getIdToken().getJwtToken();
};
```

## 통합 테스트 시나리오

### 시나리오 1: 완전한 플로우 (Mock 데이터)

```bash
# 1. 백엔드 시작
make start

# 2. 프론트엔드 시작
cd frontend && npm start

# 3. 브라우저에서 http://localhost:3000 접속
# 4. 이미지 선택 → 스타일 선택 → 생성 버튼 클릭
# 5. JobStatus 컴포넌트가 Mock 완료 상태 표시 (5초 후)
```

### 시나리오 2: 실제 API 통합

```bash
# 1. 백엔드 API 호출 확인
curl -X POST http://localhost:3001/upload \
  -H "Content-Type: application/json" \
  -d '{
    "fileName": "test.jpg",
    "fileSize": 1024000,
    "contentType": "image/jpeg"
  }'

# 2. 반환된 uploadUrl로 파일 업로드
# 3. fileKey로 이미지 생성 요청
curl -X POST http://localhost:3001/generate \
  -H "Content-Type: application/json" \
  -d '{
    "fileKey": "uploads/...",
    "prompt": "Create a professional profile photo"
  }'
```

## 다음 단계

### 즉시 할 수 있는 것 ✅

1. **로컬 테스트**
   - SAM Local API + React 개발 서버로 UI/UX 테스트
   - 스타일 선택 및 프롬프트 생성 테스트
   - Mock 데이터로 완전한 플로우 확인

2. **스타일링**
   - CSS 파일 작성 (GeneratePage.css, StyleSelector.css 등)
   - 반응형 디자인
   - 로딩 애니메이션

### 백엔드 작업 필요 ⏳

1. **Job 조회 API 추가**
   ```yaml
   # template.yaml에 추가
   Events:
     GetJobEvent:
       Type: HttpApi
       Properties:
         ApiId: !Ref HttpApi
         Path: /jobs/{jobId}
         Method: GET
   ```

2. **사용자 정보 API 추가**
   ```yaml
   Events:
     GetUserEvent:
       Type: HttpApi
       Properties:
         ApiId: !Ref HttpApi
         Path: /user/me
         Method: GET
   ```

3. **Lambda 함수 구현**
   - `backend/lambda/api/api_manager.py`에 라우팅 추가
   - GET 메서드 핸들링

### 프로덕션 준비 🚀

1. **Cognito 통합**
   - AWS Amplify 설치: `npm install aws-amplify`
   - Cognito 설정
   - 실제 JWT 토큰 사용

2. **에러 처리 강화**
   - 네트워크 에러
   - 재시도 로직
   - 사용자 친화적 메시지

3. **성능 최적화**
   - 이미지 미리보기
   - 업로드 진행률
   - 캐싱

## 참고 문서

- [API 명세서](../API_SPECIFICATION.md)
- [SAM 로컬 테스트](../SAM_LOCAL_TESTING.md)
- [클라이언트 구현 가이드](./CLIENT_IMPLEMENTATION.md)
