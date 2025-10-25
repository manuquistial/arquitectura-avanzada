import axios from 'axios';
import { getSession } from 'next-auth/react';
import type {
  CitizenCreate,
  CitizenResponse,
  CitizenUnregister,
  UploadURLRequest,
  UploadURLResponse,
  DownloadURLRequest,
  DownloadURLResponse,
  ConfirmUploadRequest,
  DocumentSearchResponse,
  TransferInitiateRequest,
  TransferResponse,
  TransferStatusResponse,
  SignDocumentRequest,
  SignDocumentResponse,
  SignatureStatusResponse,
  RegisterCitizenRequest,
  UnregisterCitizenRequest,
  AuthenticateDocumentRequest,
  SyncDocumentsRequest,
  OperatorInfo,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  DashboardStats,
  RecentActivity,
  APIError
} from '../types/api';

// Service URLs - from environment variables (configured via Kubernetes)
const AUTH_SERVICE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL;
const CITIZEN_SERVICE_URL = process.env.NEXT_PUBLIC_CITIZEN_SERVICE_URL;
const INGESTION_SERVICE_URL = process.env.NEXT_PUBLIC_INGESTION_SERVICE_URL;
const SIGNATURE_SERVICE_URL = process.env.NEXT_PUBLIC_SIGNATURE_SERVICE_URL;
const TRANSFER_SERVICE_URL = process.env.NEXT_PUBLIC_TRANSFER_SERVICE_URL;
const MINTIC_SERVICE_URL = process.env.NEXT_PUBLIC_MINTIC_SERVICE_URL;

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || '',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token from NextAuth session
api.interceptors.request.use(
  async (config) => {
    try {
      const session = await getSession();
      if (session?.accessToken) {
        config.headers.Authorization = `Bearer ${session.accessToken}`;
      }
    } catch (error) {
      console.error('Error getting session:', error);
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
      // Unauthorized - redirect to login
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// API Service Functions
export const apiService = {
  // Dashboard functionality removed - read models service eliminated

  // Documents API calls - using Ingestion service
  async getDocuments(citizenId?: string, userRoles?: string[]) {
    try {
      // Si es admin, usar un ID por defecto si no se proporciona uno
      if (userRoles?.includes('admin') && !citizenId) {
        citizenId = '1234567890';
      }
      
      if (!citizenId) {
        // Return empty array silently instead of warning
        return [];
      }
      // Send citizen_id as string to backend
      const response = await api.get(`${INGESTION_SERVICE_URL}/api/documents/`, {
        params: { citizen_id: citizenId }
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching documents:', error);
      return [];
    }
  },

  async getUploadUrl(filename: string, contentType: string, title: string, citizenId: string) {
    try {
      const response = await api.post(`${INGESTION_SERVICE_URL}/api/documents/upload-url`, {
        filename,
        content_type: contentType,
        title,
        citizen_id: citizenId
      });
      return response.data;
    } catch (error) {
      console.error('Error getting upload URL:', error);
      throw error;
    }
  },

  async confirmUpload(documentId: string, sha256: string, size: number) {
    try {
      const response = await api.post(`${INGESTION_SERVICE_URL}/api/documents/confirm-upload`, {
        document_id: documentId,
        sha256,
        size
      });
      return response.data;
    } catch (error) {
      console.error('Error confirming upload:', error);
      throw error;
    }
  },

  async getDownloadUrl(documentId: string) {
    try {
      const response = await api.post(`${INGESTION_SERVICE_URL}/api/documents/download-url`, {
        document_id: documentId
      });
      return response.data;
    } catch (error) {
      console.error('Error getting download URL:', error);
      throw error;
    }
  },

  async deleteDocument(documentId: string, citizenId: string) {
    try {
      const response = await api.delete(`${INGESTION_SERVICE_URL}/api/documents/${documentId}`, {
        params: { citizen_id: citizenId }
      });
      return response.data;
    } catch (error) {
      console.error('Error deleting document:', error);
      throw error;
    }
  },

  async uploadDocumentDirect(file: File, citizenId: string, title: string, description?: string) {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('citizen_id', citizenId);
      formData.append('title', title);
      if (description) {
        formData.append('description', description);
      }

      const response = await api.post(`${INGESTION_SERVICE_URL}/api/documents/upload-direct`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      console.error('Error uploading document directly:', error);
      throw error;
    }
  },

  // Document search functionality removed - metadata service eliminated

  // Transfers API calls - using Transfer service
  async getTransfers(citizenId?: string, userRoles?: string[]) {
    try {
      // Si es admin, no necesita citizenId específico
      if (userRoles?.includes('admin')) {
        // Para admin, podríamos obtener todas las transferencias o usar un ID por defecto
        const response = await api.get(`${TRANSFER_SERVICE_URL}/`, {
          params: { citizen_id: citizenId || '1234567890' }
        });
        return response.data;
      }
      
      if (!citizenId) {
        console.warn('No citizenId provided for getTransfers');
        return [];
      }
      const response = await api.get(`${TRANSFER_SERVICE_URL}/`, {
        params: { citizen_id: citizenId }
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching transfers:', error);
      return [];
    }
  },

  async createTransfer(transferData: any) {
    try {
      const response = await api.post(`${TRANSFER_SERVICE_URL}/initiate`, transferData);
      return response.data;
    } catch (error) {
      console.error('Error creating transfer:', error);
      throw error;
    }
  },

  async getTransferStatus(transferId: string) {
    try {
      const response = await api.get(`${TRANSFER_SERVICE_URL}/status/${transferId}`);
      return response.data;
    } catch (error) {
      console.error('Error getting transfer status:', error);
      throw error;
    }
  },

  async acceptTransfer(transferId: string) {
    try {
      const response = await api.post(`${TRANSFER_SERVICE_URL}/${transferId}/accept`);
      return response.data;
    } catch (error) {
      console.error('Error accepting transfer:', error);
      throw error;
    }
  },

  async rejectTransfer(transferId: string) {
    try {
      const response = await api.post(`${TRANSFER_SERVICE_URL}/${transferId}/reject`);
      return response.data;
    } catch (error) {
      console.error('Error rejecting transfer:', error);
      throw error;
    }
  },

  // Notifications functionality removed - notification service eliminated

  // Signature API calls - using Signature service
  async signDocument(documentId: string, signatureData: any) {
    try {
      const response = await api.post(`${SIGNATURE_SERVICE_URL}/sign`, {
        document_id: documentId,
        ...signatureData,
      });
      return response.data;
    } catch (error) {
      console.error('Error signing document:', error);
      throw error;
    }
  },

  async getSignatureStatus(documentId: string) {
    try {
      const response = await api.get(`${SIGNATURE_SERVICE_URL}/status/${documentId}`);
      return response.data;
    } catch (error) {
      console.error('Error getting signature status:', error);
      throw error;
    }
  },

  async verifySignature(documentId: string) {
    try {
      const response = await api.post(`${SIGNATURE_SERVICE_URL}/verify`, {
        document_id: documentId
      });
      return response.data;
    } catch (error) {
      console.error('Error verifying signature:', error);
      throw error;
    }
  },


  // Citizen API calls - using Citizen service
  async registerCitizen(citizenData: CitizenCreate): Promise<CitizenResponse> {
    try {
      const response = await api.post(`${CITIZEN_SERVICE_URL}/register`, citizenData);
      return response.data;
    } catch (error) {
      console.error('Error registering citizen:', error);
      throw error;
    }
  },

  async getCitizen(citizenId: string): Promise<CitizenResponse> {
    try {
      const response = await api.get(`${CITIZEN_SERVICE_URL}/${citizenId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching citizen:', error);
      throw error;
    }
  },

  async unregisterCitizen(citizenData: CitizenUnregister): Promise<void> {
    try {
      const response = await api.delete(`${CITIZEN_SERVICE_URL}/unregister`, {
        data: citizenData
      });
      return response.data;
    } catch (error) {
      console.error('Error unregistering citizen:', error);
      throw error;
    }
  },


  // User management API calls
  async getCurrentUser() {
    try {
      const response = await api.get(`${CITIZEN_SERVICE_URL}/me`);
      return response.data;
    } catch (error) {
      console.error('Error fetching current user:', error);
      throw error;
    }
  },

  async updateUser(userId: string, userData: any) {
    try {
      const response = await api.patch(`${CITIZEN_SERVICE_URL}/${userId}`, userData);
      return response.data;
    } catch (error) {
      console.error('Error updating user:', error);
      throw error;
    }
  },

  // MinTIC Hub API calls - using MinTIC Client service
  async syncDocumentsWithHub(citizenId: string, documentIds?: string[], syncType = 'full') {
    try {
      const response = await api.post(`${MINTIC_SERVICE_URL}/sync/documents`, {
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
      const response = await api.get(`${MINTIC_SERVICE_URL}/sync/status/${citizenId}`);
      return response.data;
    } catch (error) {
      console.error('Error getting sync status:', error);
      throw error;
    }
  },

  async validateDocumentWithHub(documentId: string, documentHash: string, citizenId: string) {
    try {
      const response = await api.post(`${MINTIC_SERVICE_URL}/authenticate-document`, {
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


  async registerCitizenWithHub(citizenData: any) {
    try {
      const response = await api.post(`${MINTIC_SERVICE_URL}/register-citizen`, citizenData);
      return response.data;
    } catch (error) {
      console.error('Error registering citizen with hub:', error);
      throw error;
    }
  },

  async authenticateDocumentWithHub(documentData: any) {
    try {
      const response = await api.post(`${MINTIC_SERVICE_URL}/authenticate-document`, documentData);
      return response.data;
    } catch (error) {
      console.error('Error authenticating document with hub:', error);
      throw error;
    }
  },

  // Auth service calls
  async registerUser(userData: RegisterRequest): Promise<RegisterResponse> {
    try {
      const response = await api.post(`${AUTH_SERVICE_URL}/register`, userData);
      return response.data;
    } catch (error) {
      console.error('Error registering user:', error);
      throw error;
    }
  },

  async loginUser(credentials: LoginRequest): Promise<LoginResponse> {
    try {
      const response = await api.post(`${AUTH_SERVICE_URL}/login`, credentials);
      return response.data;
    } catch (error) {
      console.error('Error logging in user:', error);
      throw error;
    }
  },

  // Operator management API calls - using Transfer service
  async getOperators() {
    try {
      const response = await api.get(`${TRANSFER_SERVICE_URL}/operators`);
      return response.data;
    } catch (error) {
      console.error('Error fetching operators:', error);
      return { operators: [] };
    }
  },

  async registerOperator(operatorData: any) {
    try {
      const response = await api.post(`${TRANSFER_SERVICE_URL}/register-operator`, operatorData);
      return response.data;
    } catch (error) {
      console.error('Error registering operator:', error);
      throw error;
    }
  },

  async getOperator(operatorId: string) {
    try {
      const response = await api.get(`${TRANSFER_SERVICE_URL}/operators/${operatorId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching operator:', error);
      throw error;
    }
  },

  // MinTIC Operator management API calls - using MinTIC Client service
  async registerMinTICOperator(operatorData: {
    name: string;
    address: string;
    contactMail: string;
    participants: string[];
  }) {
    try {
      const response = await api.post(`${MINTIC_SERVICE_URL}/register-operator`, operatorData);
      return response.data;
    } catch (error) {
      console.error('Error registering MinTIC operator:', error);
      throw error;
    }
  },

  async getMinTICOperators() {
    try {
      const response = await api.get(`${MINTIC_SERVICE_URL}/operators/local`);
      return response.data;
    } catch (error) {
      console.error('Error fetching MinTIC operators:', error);
      return { operators: [], total: 0 };
    }
  },

  async getMinTICOperator(operatorId: number) {
    try {
      const response = await api.get(`${MINTIC_SERVICE_URL}/operators/local/${operatorId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching MinTIC operator:', error);
      throw error;
    }
  },

  async deactivateMinTICOperator(operatorId: number) {
    try {
      const response = await api.put(`${MINTIC_SERVICE_URL}/operators/local/${operatorId}/deactivate`);
      return response.data;
    } catch (error) {
      console.error('Error deactivating MinTIC operator:', error);
      throw error;
    }
  },

  async deleteMinTICOperator(operatorId: number) {
    try {
      const response = await api.delete(`${MINTIC_SERVICE_URL}/operators/local/${operatorId}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting MinTIC operator:', error);
      throw error;
    }
  },

  async getDashboardStats() {
    try {
      // Mock data for now - replace with actual API call when backend is ready
      return {
        totalDocuments: 0,
        pendingTransfers: 0,
        signedDocuments: 0,
        sharedDocuments: 0
      };
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
      throw error;
    }
  },

  async getRecentActivities() {
    try {
      // Mock data for now - replace with actual API call when backend is ready
      return [];
    } catch (error) {
      console.error('Error fetching recent activities:', error);
      throw error;
    }
  },
};

