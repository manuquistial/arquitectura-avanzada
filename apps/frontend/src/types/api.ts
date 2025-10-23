/**
 * API Types - Compatible with Backend Services
 * These types match the schemas defined in the backend services
 */

// ========================================
// Citizen Service Types
// ========================================

export interface CitizenCreate {
  id: string; // Must be exactly 10 digits
  name: string;
  address: string;
  email: string;
  operator_id: string;
  operator_name: string;
}

export interface CitizenResponse {
  id: string;
  name: string;
  address: string;
  email: string;
  operator_id: string;
  operator_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CitizenUnregister {
  id: string;
  operator_id: string;
}

// ========================================
// Ingestion Service Types
// ========================================

export interface UploadURLRequest {
  citizen_id: number;
  filename: string;
  content_type: string;
  title: string;
  description?: string;
}

export interface UploadURLResponse {
  upload_url: string;
  document_id: string;
  blob_name: string;
  expires_in: number;
}

export interface DownloadURLRequest {
  document_id: string;
}

export interface DownloadURLResponse {
  download_url: string;
  expires_in: number;
}

export interface ConfirmUploadRequest {
  document_id: string;
  sha256: string;
  size: number;
}

// ========================================
// Metadata Service Types
// ========================================

export interface DocumentMetadataCreate {
  citizen_id: string;
  title: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  sha256_hash?: string;
  issuer?: string;
  tags?: string;
  description?: string;
}

export interface DocumentMetadataResponse {
  id: string;
  citizen_id: string;
  title: string;
  filename: string;
  content_type: string;
  size_bytes?: number;
  sha256_hash?: string;
  blob_name: string;
  storage_provider: string;
  status: string;
  is_uploaded: boolean;
  state: string;
  worm_locked: boolean;
  signed_at?: string;
  retention_until?: string;
  hub_signature_ref?: string;
  legal_hold: boolean;
  lifecycle_tier: string;
  description?: string;
  tags?: string;
  is_deleted: boolean;
  created_at: string;
  updated_at?: string;
}

export interface DocumentSearchResponse {
  documents: SearchResult[];
  total: number;
  page: number;
  page_size: number;
  took_ms: number;
}

export interface SearchResult {
  id: string;
  title: string;
  description?: string;
  filename: string;
  created_at: string;
  score: number;
}

// ========================================
// Signature Service Types
// ========================================

export interface SignDocumentRequest {
  document_id: string;
  citizen_id: string;
  signature_data?: any;
}

export interface SignDocumentResponse {
  success: boolean;
  signature_id?: string;
  message: string;
}

export interface SignatureStatusResponse {
  document_id: string;
  is_signed: boolean;
  signed_at?: string;
  signature_valid: boolean;
  hub_authenticated: boolean;
}

// ========================================
// Transfer Service Types
// ========================================

export interface TransferInitiateRequest {
  from_citizen_id: number;
  to_citizen_id: number;
  document_ids: string[];
  message?: string;
}

export interface TransferResponse {
  transfer_id: string;
  status: string;
  from_citizen_id: number;
  to_citizen_id: number;
  document_ids: string[];
  message?: string;
  created_at: string;
  expires_at: string;
}

export interface TransferStatusResponse {
  transfer_id: string;
  status: 'pending' | 'accepted' | 'rejected' | 'expired';
  from_citizen_id: number;
  to_citizen_id: number;
  document_ids: string[];
  message?: string;
  created_at: string;
  expires_at: string;
  accepted_at?: string;
  rejected_at?: string;
}

// ========================================
// MinTIC Service Types
// ========================================

export interface MinTICResponse {
  ok: boolean;
  status: number;
  message: string;
  data?: any;
}

export interface RegisterCitizenRequest {
  id: string; // 10-digit citizen ID as string
  name: string;
  address: string;
  email: string;
  operatorId: string;
  operatorName: string;
}

export interface UnregisterCitizenRequest {
  id: string;
  operatorId: string;
}

export interface AuthenticateDocumentRequest {
  document_id: string;
  document_hash: string;
  citizen_id: string;
  operator_id: string;
}

export interface SyncDocumentsRequest {
  citizen_id: string;
  document_ids?: string[];
  sync_type: 'full' | 'incremental';
}

export interface OperatorInfo {
  id: string;
  name: string;
  status: string;
  created_at: string;
}

// ========================================
// Auth Service Types
// ========================================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  id: string;
  email: string;
  name: string;
  given_name?: string;
  family_name?: string;
  roles: string[];
  permissions: string[];
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
  given_name?: string;
  family_name?: string;
}

export interface RegisterResponse {
  id: string;
  email: string;
  name: string;
  given_name?: string;
  family_name?: string;
  roles: string[];
  permissions: string[];
}

// ========================================
// Read Models Service Types
// ========================================

export interface DashboardStats {
  totalDocuments: number;
  signedDocuments: number;
  pendingTransfers: number;
  sharedDocuments: number;
}

export interface RecentActivity {
  id: string;
  type: 'document_uploaded' | 'document_signed' | 'transfer_received' | 'transfer_sent';
  description: string;
  timestamp: string;
  citizen_id: string;
  document_id?: string;
  transfer_id?: string;
}

// ========================================
// API Error Types
// ========================================

export interface APIError {
  detail: string;
  status_code: number;
  error_code?: string;
}

export interface ValidationError {
  detail: Array<{
    loc: string[];
    msg: string;
    type: string;
  }>;
  status_code: 422;
}
