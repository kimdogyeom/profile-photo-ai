import axios from 'axios';
import { getIdToken, isAuthenticated, logout, refreshTokens } from './auth';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;

// Get auth token from Cognito
const getAuthToken = async () => {
  if (!isAuthenticated()) {
    // Try to refresh tokens
    try {
      await refreshTokens();
    } catch (error) {
      console.error('Failed to refresh token:', error);
      return null;
    }
  }
  return getIdToken();
};

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

apiClient.interceptors.request.use(async (config) => {
  const token = await getAuthToken();
  config.headers = config.headers || {};
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Response interceptor for 401 errors
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      console.error('Unauthorized - token may be invalid or expired');
      logout();
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);

export const getUploadUrl = async (file) => {
  const response = await apiClient.post('/upload', {
    fileName: file.name,
    fileSize: file.size,
    contentType: file.type
  });
  
  return {
    uploadUrl: response.data.uploadUrl,
    uploadMethod: response.data.uploadMethod,
    uploadFields: response.data.uploadFields,
    fileKey: response.data.fileKey,
    expiresIn: response.data.expiresIn
  };
};

export const uploadToS3 = async ({ uploadUrl, uploadMethod = 'POST', uploadFields = {}, file }) => {
  if (uploadMethod === 'POST') {
    const formData = new FormData();
    Object.entries(uploadFields).forEach(([key, value]) => {
      formData.append(key, value);
    });
    formData.append('file', file);

    const response = await fetch(uploadUrl, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`S3 upload failed with status ${response.status}`);
    }

    return;
  }

  const response = await fetch(uploadUrl, {
    method: uploadMethod,
    body: file,
    headers: {
      'Content-Type': file.type
    }
  });

  if (!response.ok) {
    throw new Error(`S3 upload failed with status ${response.status}`);
  }
};

export const generateImage = async ({ fileKey, prompt, style }) => {
  const response = await apiClient.post('/generate', {
    fileKey,
    prompt,
    style  // 스타일 정보 포함
  });
  
  return {
    jobId: response.data.jobId,
    status: response.data.status,
    remainingQuota: response.data.remainingQuota
  };
};

export const uploadImage = async (file) => {
  const { uploadUrl, uploadMethod, uploadFields, fileKey } = await getUploadUrl(file);
  await uploadToS3({ uploadUrl, uploadMethod, uploadFields, file });
  return { fileKey };
};

export const getJobStatus = async (jobId) => {
  const response = await apiClient.get(`/jobs/${jobId}`);
  return response.data;
};

export const getDownloadUrl = async (jobId) => {
  const response = await apiClient.get(`/jobs/${jobId}/download`);
  return response.data.downloadUrl;
};

export const getUserInfo = async () => {
  const response = await apiClient.get('/user/me');
  return response.data;
};

export const getUserJobs = async (limit = 50, nextToken = null) => {
  const params = { limit };
  if (nextToken) {
    params.nextToken = nextToken;
  }
  
  const response = await apiClient.get('/user/jobs', { params });
  return {
    jobs: response.data.jobs || [],
    nextToken: response.data.nextToken || null,
    hasMore: Boolean(response.data.hasMore)
  };
};
