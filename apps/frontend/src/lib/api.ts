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
const METADATA_SERVICE_URL = process.env.NEXT_PUBLIC_METADATA_SERVICE_URL;
const NOTIFICATION_SERVICE_URL = process.env.NEXT_PUBLIC_NOTIFICATION_SERVICE_URL;

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
      if (session?.user?.id) {
        // For Citizen Service, we need to use the user_id directly
        // The Citizen Service will verify the token format
        // Since NextAuth token might not be compatible, we'll send the user_id as a simple token
        // TODO: Generate proper HS256 JWT token with shared secret
        
        // For now, try to use accessToken if available, otherwise use a simple format
        if (session?.accessToken) {
          config.headers.Authorization = `Bearer ${session.accessToken}`;
        } else {
          // Fallback: send user_id as token (will need to be handled by backend)
          // This is a temporary solution until we implement proper JWT token generation
          console.warn('No accessToken available, using user_id as fallback');
        }
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

  async downloadDocument(documentId: string, filename: string) {
    try {
      const response = await api.get(`${INGESTION_SERVICE_URL}/api/documents/download/${documentId}`, {
        responseType: 'blob'
      });
      
      // Create blob URL and trigger download
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error downloading document:', error);
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

  // Metadata Service API calls
  async getDocumentMetadata(citizenId: string) {
    try {
      if (!METADATA_SERVICE_URL) {
        console.warn('NEXT_PUBLIC_METADATA_SERVICE_URL not configured');
        return [];
      }
      const response = await api.get(`${METADATA_SERVICE_URL}/api/metadata/documents/citizen/${citizenId}`);
      // The response is an object with 'documents' array, not a direct array
      if (response.data && Array.isArray(response.data.documents)) {
        return response.data.documents;
      } else if (Array.isArray(response.data)) {
        // Fallback: if response.data is already an array, return it
        return response.data;
      }
      return [];
    } catch (error) {
      console.error('Error fetching document metadata:', error);
      return [];
    }
  },

  async searchDocuments(query: string, citizenId?: string) {
    try {
      if (!METADATA_SERVICE_URL) {
        console.warn('NEXT_PUBLIC_METADATA_SERVICE_URL not configured');
        return { documents: [], total: 0 };
      }
      const response = await api.post(`${METADATA_SERVICE_URL}/api/metadata/search`, {
        query,
        citizen_id: citizenId,
      });
      return response.data;
    } catch (error) {
      console.error('Error searching documents:', error);
      return { documents: [], total: 0 };
    }
  },

  // Transfers API calls - using Transfer service
  async getTransfers(citizenId?: string, userRoles?: string[]) {
    try {
      // Si es admin, no necesita citizenId específico
      if (userRoles?.includes('admin')) {
        // Para admin, podríamos obtener todas las transferencias o usar un ID por defecto
        const response = await api.get(`${TRANSFER_SERVICE_URL}/api`, {
          params: { citizen_id: citizenId || '1234567890' }
        });
        return response.data;
      }
      
      if (!citizenId) {
        console.warn('No citizenId provided for getTransfers');
        return [];
      }
      const response = await api.get(`${TRANSFER_SERVICE_URL}/api`, {
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
      const response = await api.post(`${TRANSFER_SERVICE_URL}/api/initiate`, transferData);
      return response.data;
    } catch (error) {
      console.error('Error creating transfer:', error);
      throw error;
    }
  },

  async getTransferStatus(transferId: string) {
    try {
      const response = await api.get(`${TRANSFER_SERVICE_URL}/api/status/${transferId}`);
      return response.data;
    } catch (error) {
      console.error('Error getting transfer status:', error);
      throw error;
    }
  },

  async acceptTransfer(transferId: string) {
    try {
      const response = await api.post(`${TRANSFER_SERVICE_URL}/api/${transferId}/accept`);
      return response.data;
    } catch (error) {
      console.error('Error accepting transfer:', error);
      throw error;
    }
  },

  async rejectTransfer(transferId: string) {
    try {
      const response = await api.post(`${TRANSFER_SERVICE_URL}/api/${transferId}/reject`);
      return response.data;
    } catch (error) {
      console.error('Error rejecting transfer:', error);
      throw error;
    }
  },

  // Notification Service API calls
  async getNotificationStats() {
    try {
      if (!NOTIFICATION_SERVICE_URL) {
        console.warn('NEXT_PUBLIC_NOTIFICATION_SERVICE_URL not configured');
        return { total_notifications: 0 };
      }
      const response = await api.get(`${NOTIFICATION_SERVICE_URL}/api/notifications/stats`);
      return response.data;
    } catch (error) {
      console.error('Error fetching notification stats:', error);
      return { total_notifications: 0 };
    }
  },

  async getUserNotifications(citizenId: string) {
    try {
      if (!NOTIFICATION_SERVICE_URL) {
        console.warn('NEXT_PUBLIC_NOTIFICATION_SERVICE_URL not configured');
        return [];
      }
      const response = await api.get(`${NOTIFICATION_SERVICE_URL}/api/notifications/user/${citizenId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching user notifications:', error);
      return [];
    }
  },

  // Signature API calls - using Signature service
  async signDocument(documentId: string, signatureData: SignDocumentRequest) {
    try {
      const response = await api.post(`${SIGNATURE_SERVICE_URL}/api/signature/sign`, {
        document_id: documentId,
        citizen_id: signatureData.citizen_id,
        signature_type: signatureData.signature_type || "PAdES",
        document_title: signatureData.document_title || "",
      });
      return response.data;
    } catch (error) {
      console.error('Error signing document:', error);
      throw error;
    }
  },

  async getSignatureStatus(documentId: string) {
    // Note: This endpoint doesn't exist in the backend
    // Using verifySignature instead to check signature status
    try {
      return await this.verifySignature(documentId);
    } catch (error) {
      console.error('Error getting signature status:', error);
      throw error;
    }
  },

  async verifySignature(documentId: string) {
    try {
      const response = await api.post(`${SIGNATURE_SERVICE_URL}/api/signature/verify`, {
        signed_document_id: documentId  // Backend expects signed_document_id
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
      const response = await api.post(`${CITIZEN_SERVICE_URL}/api/citizens/register`, citizenData);
      return response.data;
    } catch (error) {
      console.error('Error registering citizen:', error);
      throw error;
    }
  },

  async getCitizen(citizenId: string): Promise<CitizenResponse> {
    try {
      const response = await api.get(`${CITIZEN_SERVICE_URL}/api/citizens/${citizenId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching citizen:', error);
      throw error;
    }
  },

  async unregisterCitizen(citizenData: CitizenUnregister): Promise<void> {
    try {
      const response = await api.delete(`${CITIZEN_SERVICE_URL}/api/citizens/unregister`, {
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
      const response = await api.get(`${CITIZEN_SERVICE_URL}/api/users/me`);
      return response.data;
    } catch (error) {
      console.error('Error fetching current user:', error);
      throw error;
    }
  },

  async getAllUsers(skip: number = 0, limit: number = 100) {
    try {
      const response = await api.get(`${CITIZEN_SERVICE_URL}/api/users/`, {
        params: { skip, limit }
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching users:', error);
      throw error;
    }
  },

  async getUserById(userId: string) {
    try {
      const response = await api.get(`${CITIZEN_SERVICE_URL}/api/users/${userId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching user:', error);
      throw error;
    }
  },

  async updateUser(userId: string, userData: any) {
    try {
      const response = await api.patch(`${CITIZEN_SERVICE_URL}/api/users/${userId}`, userData);
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

  async getDashboardStats(citizenId?: string) {
    try {
      // Use provided citizenId or default for testing
      const id = citizenId || '1234567890';
      
      // Get documents from Ingestion Service
      const documents = await this.getDocuments(id);
      const totalDocuments = documents.length;
      
      // Count signed documents (filter by status === 'signed' or state === 'SIGNED')
      const signedDocuments = documents.filter((doc: any) => 
        doc.status === 'signed' || doc.state === 'SIGNED'
      ).length;
      
      // Get transfers from Transfer Service
      const transfers = await this.getTransfers(id);
      const pendingTransfers = transfers.filter((t: any) => 
        t.status === 'pending'
      ).length;
      
      // Get notification stats from Notification Service
      const notifStats = await this.getNotificationStats();
      
      return {
        totalDocuments,
        signedDocuments,
        pendingTransfers,
        sharedDocuments: notifStats.total_notifications || 0,
      };
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
      return {
        totalDocuments: 0,
        signedDocuments: 0,
        pendingTransfers: 0,
        sharedDocuments: 0,
      };
    }
  },

  async getRecentActivities(citizenId?: string) {
    try {
      // Use provided citizenId or default for testing
      const id = citizenId || '1234567890';
      
      // Get recent documents from Ingestion Service
      const documents = await this.getDocuments(id);
      
      // Get recent transfers
      const transfers = await this.getTransfers(id);
      
      // Combine and sort by date
      const activities: any[] = [];
      
      // Add document activities
      documents.slice(0, 5).forEach((doc: any) => {
        activities.push({
          id: doc.id,
          type: doc.status === 'signed' ? 'document_signed' : 'document_uploaded',
          description: `Documento ${doc.title || doc.filename} ${doc.status === 'signed' ? 'firmado' : 'subido'}`,
          timestamp: doc.created_at || doc.updated_at,
          citizen_id: id,
          document_id: doc.id,
        });
      });
      
      // Add transfer activities
      transfers.slice(0, 3).forEach((transfer: any) => {
        activities.push({
          id: transfer.id,
          type: transfer.status === 'accepted' ? 'transfer_received' : 'transfer_sent',
          description: `Transferencia ${transfer.status === 'accepted' ? 'recibida' : 'enviada'}`,
          timestamp: transfer.created_at,
          citizen_id: id,
          transfer_id: transfer.id,
        });
      });
      
      // Sort by timestamp (most recent first)
      activities.sort((a, b) => 
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );
      
      return activities.slice(0, 10);
    } catch (error) {
      console.error('Error fetching recent activities:', error);
      return [];
    }
  },
};

