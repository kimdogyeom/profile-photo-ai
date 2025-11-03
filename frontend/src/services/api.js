import axios from 'axios';
import { getIdToken, isAuthenticated, refreshTokens } from './auth';

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
      // Redirect to login
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
    fileKey: response.data.fileKey,
    expiresIn: response.data.expiresIn
  };
};

export const uploadToS3 = async (uploadUrl, file) => {
  await fetch(uploadUrl, {
    method: 'PUT',
    body: file,
    headers: {
      'Content-Type': file.type,
      'x-amz-server-side-encryption': 'AES256'
    }
  });
};

export const generateImage = async ({ fileKey, prompt }) => {
  const response = await apiClient.post('/generate', {
    fileKey,
    prompt
  });
  
  return {
    jobId: response.data.jobId,
    status: response.data.status,
    remainingQuota: response.data.remainingQuota
  };
};

export const uploadImage = async (file) => {
  const { uploadUrl, fileKey } = await getUploadUrl(file);
  await uploadToS3(uploadUrl, file);
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
