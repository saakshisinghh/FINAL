import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API,
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth API
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  getMe: () => api.get('/auth/me'),
};

// Chat API
export const chatAPI = {
  startChat: () => api.post('/chat/start'),
  sendMessage: (sessionId, message) => api.post(`/chat/${sessionId}/message`, { message }),
  getHistory: (sessionId) => api.get(`/chat/${sessionId}/history`),
};

// Loan API
export const loanAPI = {
  apply: (data) => api.post('/loans/apply', data),
  getAll: () => api.get('/loans'),
  getOne: (id) => api.get(`/loans/${id}`),
};

// Document API
export const documentAPI = {
  upload: (file, docType, loanId) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('doc_type', docType);
    if (loanId) formData.append('loan_application_id', loanId);
    return api.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  getAll: () => api.get('/documents'),
};

// Sanction Letter API
export const sanctionAPI = {
  download: (loanId) => api.get(`/sanction/${loanId}/download`, {
    responseType: 'blob',
  }),
};

// Dashboard API
export const dashboardAPI = {
  getStats: () => api.get('/dashboard/stats'),
};

// Admin API
export const adminAPI = {
  initData: () => api.post('/admin/init-data'),
};

export default api;