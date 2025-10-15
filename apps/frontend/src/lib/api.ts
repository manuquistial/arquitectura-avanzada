import axios from 'axios';
import { useAuthStore } from '@/store/authStore';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Unauthorized - logout user
      useAuthStore.getState().logout();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// API Service Functions
export const apiService = {
  // Dashboard API calls
  async getDashboardStats() {
    try {
      const response = await api.get('/api/documents/stats');
      return response.data;
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
      // Return mock data as fallback
      return {
        totalDocuments: 0,
        signedDocuments: 0,
        pendingTransfers: 0,
        sharedDocuments: 0,
      };
    }
  },

  async getRecentActivities() {
    try {
      const response = await api.get('/api/activities/recent');
      return response.data;
    } catch (error) {
      console.error('Error fetching recent activities:', error);
      return [];
    }
  },

  // Documents API calls
  async getDocuments() {
    try {
      const response = await api.get('/api/documents');
      return response.data;
    } catch (error) {
      console.error('Error fetching documents:', error);
      return [];
    }
  },

  async uploadDocument(file: File, metadata: any) {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('metadata', JSON.stringify(metadata));

      const response = await api.post('/api/documents/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      console.error('Error uploading document:', error);
      throw error;
    }
  },

  async downloadDocument(documentId: string) {
    try {
      const response = await api.get(`/api/documents/${documentId}/download`, {
        responseType: 'blob',
      });
      return response.data;
    } catch (error) {
      console.error('Error downloading document:', error);
      throw error;
    }
  },

  async deleteDocument(documentId: string) {
    try {
      const response = await api.delete(`/api/documents/${documentId}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting document:', error);
      throw error;
    }
  },

  // Transfers API calls
  async getTransfers() {
    try {
      const response = await api.get('/api/transfers');
      return response.data;
    } catch (error) {
      console.error('Error fetching transfers:', error);
      return [];
    }
  },

  async createTransfer(transferData: any) {
    try {
      const response = await api.post('/api/transfers', transferData);
      return response.data;
    } catch (error) {
      console.error('Error creating transfer:', error);
      throw error;
    }
  },

  async acceptTransfer(transferId: string) {
    try {
      const response = await api.post(`/api/transfers/${transferId}/accept`);
      return response.data;
    } catch (error) {
      console.error('Error accepting transfer:', error);
      throw error;
    }
  },

  async rejectTransfer(transferId: string) {
    try {
      const response = await api.post(`/api/transfers/${transferId}/reject`);
      return response.data;
    } catch (error) {
      console.error('Error rejecting transfer:', error);
      throw error;
    }
  },

  // Notifications API calls
  async getNotifications() {
    try {
      const response = await api.get('/api/notifications');
      return response.data;
    } catch (error) {
      console.error('Error fetching notifications:', error);
      return [];
    }
  },

  async markNotificationAsRead(notificationId: string) {
    try {
      const response = await api.patch(`/api/notifications/${notificationId}/read`);
      return response.data;
    } catch (error) {
      console.error('Error marking notification as read:', error);
      throw error;
    }
  },

  // Signature API calls
  async signDocument(documentId: string, signatureData: any) {
    try {
      const response = await api.post(`/api/signature/sign`, {
        documentId,
        ...signatureData,
      });
      return response.data;
    } catch (error) {
      console.error('Error signing document:', error);
      throw error;
    }
  },

  // Sharing API calls
  async shareDocument(documentId: string, shareData: any) {
    try {
      const response = await api.post(`/api/sharing/share`, {
        documentId,
        ...shareData,
      });
      return response.data;
    } catch (error) {
      console.error('Error sharing document:', error);
      throw error;
    }
  },

  // Citizen API calls
  async registerCitizen(citizenData: any) {
    try {
      const response = await api.post('/api/citizens/register', citizenData);
      return response.data;
    } catch (error) {
      console.error('Error registering citizen:', error);
      throw error;
    }
  },

  async getCitizen(citizenId: string) {
    try {
      const response = await api.get(`/api/citizens/${citizenId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching citizen:', error);
      throw error;
    }
  },

  // MinTIC Hub API calls
  async syncDocumentsWithHub(citizenId: string, documentIds?: string[], syncType = 'full') {
    try {
      const response = await api.post('/api/mintic/sync/documents', {
        citizen_id: citizenId,
        document_ids: documentIds,
        sync_type: syncType
      });
      return response.data;
    } catch (error) {
      console.error('Error syncing documents with hub:', error);
      throw error;
    }
  },

  async getSyncStatus(citizenId: string) {
    try {
      const response = await api.get(`/api/mintic/sync/status/${citizenId}`);
      return response.data;
    } catch (error) {
      console.error('Error getting sync status:', error);
      throw error;
    }
  },

  async validateDocumentWithHub(documentId: string, documentHash: string, citizenId: string) {
    try {
      const response = await api.post('/api/mintic/validate/document', {
        document_id: documentId,
        document_hash: documentHash,
        citizen_id: citizenId
      });
      return response.data;
    } catch (error) {
      console.error('Error validating document with hub:', error);
      throw error;
    }
  },

  async getOperators() {
    try {
      const response = await api.get('/api/mintic/operators');
      return response.data;
    } catch (error) {
      console.error('Error getting operators:', error);
      return [];
    }
  },

  async registerCitizenWithHub(citizenData: any) {
    try {
      const response = await api.post('/api/mintic/register-citizen', citizenData);
      return response.data;
    } catch (error) {
      console.error('Error registering citizen with hub:', error);
      throw error;
    }
  },

  async authenticateDocumentWithHub(documentData: any) {
    try {
      const response = await api.post('/api/mintic/authenticate-document', documentData);
      return response.data;
    } catch (error) {
      console.error('Error authenticating document with hub:', error);
      throw error;
    }
  },
};

