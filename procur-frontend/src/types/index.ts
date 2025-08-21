// User types
export interface User {
  uid: string;
  email: string;
  display_name: string;
  photo_url?: string;
  phone_number?: string;
  company_name?: string;
  job_title?: string;
  industry?: string;
  location?: string;
  bio?: string;
  created_at: string;
  updated_at: string;
  is_verified: boolean;
  is_active: boolean;
}

export interface UserProfile {
  uid: string;
  email: string;
  display_name: string;
  photo_url?: string;
  phone_number?: string;
  company_name?: string;
  job_title?: string;
  industry?: string;
  location?: string;
  bio?: string;
  created_at: string;
  updated_at: string;
  is_verified: boolean;
  is_active: boolean;
}

// Group types
export interface Group {
  id: string;
  name: string;
  description: string;
  category: string;
  industry: string;
  privacy: 'public' | 'private' | 'invite_only';
  max_members: number;
  current_members: number;
  created_by: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  tags: string[];
  location?: string;
  website?: string;
  contact_email?: string;
}

export interface GroupMember {
  uid: string;
  display_name: string;
  email: string;
  photo_url?: string;
  role: 'owner' | 'admin' | 'member';
  joined_at: string;
  company_name?: string;
  job_title?: string;
}

export interface CreateGroupRequest {
  name: string;
  description: string;
  category: string;
  industry: string;
  privacy: 'public' | 'private' | 'invite_only';
  max_members: number;
  tags: string[];
  location?: string;
  website?: string;
  contact_email?: string;
}

// Invitation types
export interface Invitation {
  id: string;
  group_id: string;
  group_name: string;
  invited_by: string;
  invited_by_name: string;
  invited_email: string;
  status: 'pending' | 'accepted' | 'declined' | 'expired';
  role: 'admin' | 'member';
  created_at: string;
  expires_at: string;
  message?: string;
}

export interface CreateInvitationRequest {
  group_id: string;
  email: string;
  role: 'admin' | 'member';
  message?: string;
}

// Authentication types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  display_name: string;
  company_name?: string;
  job_title?: string;
  industry?: string;
  location?: string;
  phone_number?: string;
}

export interface AuthResponse {
  user: User;
  token: string;
  refresh_token: string;
}

// API Response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  has_next: boolean;
  has_prev: boolean;
}

// File upload types
export interface UploadedFile {
  id: string;
  filename: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  upload_path: string;
  uploaded_by: string;
  uploaded_at: string;
  group_id?: string;
  user_id?: string;
  is_public: boolean;
}

// Error types
export interface ApiError {
  detail: string;
  status_code: number;
  timestamp: string;
}

// Navigation types
export interface NavItem {
  label: string;
  path: string;
  icon: string;
  requiresAuth: boolean;
  children?: NavItem[];
}
