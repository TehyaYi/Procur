import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { 
  User, 
  Group, 
  Invitation, 
  LoginRequest, 
  RegisterRequest, 
  AuthResponse,
  CreateGroupRequest,
  CreateInvitationRequest,
  ApiResponse,
  PaginatedResponse,
  UploadedFile
} from '../types';

// API base URL - adjust based on your backend setup
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor to handle auth errors
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('auth_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Authentication endpoints
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const response: AxiosResponse<AuthResponse> = await this.api.post('/auth/login', credentials);
    return response.data;
  }

  async register(userData: RegisterRequest): Promise<AuthResponse> {
    const response: AxiosResponse<AuthResponse> = await this.api.post('/auth/register', userData);
    return response.data;
  }

  async logout(): Promise<void> {
    await this.api.post('/auth/logout');
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
  }

  async refreshToken(): Promise<AuthResponse> {
    const refreshToken = localStorage.getItem('refresh_token');
    const response: AxiosResponse<AuthResponse> = await this.api.post('/auth/refresh', {
      refresh_token: refreshToken
    });
    return response.data;
  }

  // User endpoints
  async getCurrentUser(): Promise<User> {
    const response: AxiosResponse<User> = await this.api.get('/users/me');
    return response.data;
  }

  async updateProfile(userData: Partial<User>): Promise<User> {
    const response: AxiosResponse<User> = await this.api.put('/users/me', userData);
    return response.data;
  }

  async getUserProfile(uid: string): Promise<User> {
    const response: AxiosResponse<User> = await this.api.get(`/users/${uid}`);
    return response.data;
  }

  // Group endpoints
  async getGroups(page: number = 1, per_page: number = 10): Promise<PaginatedResponse<Group>> {
    const response: AxiosResponse<PaginatedResponse<Group>> = await this.api.get('/groups', {
      params: { page, per_page }
    });
    return response.data;
  }

  async getGroup(groupId: string): Promise<Group> {
    const response: AxiosResponse<Group> = await this.api.get(`/groups/${groupId}`);
    return response.data;
  }

  async createGroup(groupData: CreateGroupRequest): Promise<Group> {
    const response: AxiosResponse<Group> = await this.api.post('/groups', groupData);
    return response.data;
  }

  async updateGroup(groupId: string, groupData: Partial<Group>): Promise<Group> {
    const response: AxiosResponse<Group> = await this.api.put(`/groups/${groupId}`, groupData);
    return response.data;
  }

  async deleteGroup(groupId: string): Promise<void> {
    await this.api.delete(`/groups/${groupId}`);
  }

  async joinGroup(groupId: string): Promise<void> {
    await this.api.post(`/groups/${groupId}/join`);
  }

  async leaveGroup(groupId: string): Promise<void> {
    await this.api.post(`/groups/${groupId}/leave`);
  }

  async getGroupMembers(groupId: string): Promise<User[]> {
    const response: AxiosResponse<User[]> = await this.api.get(`/groups/${groupId}/members`);
    return response.data;
  }

  async updateMemberRole(groupId: string, memberId: string, role: string): Promise<void> {
    await this.api.put(`/groups/${groupId}/members/${memberId}`, { role });
  }

  async removeMember(groupId: string, memberId: string): Promise<void> {
    await this.api.delete(`/groups/${groupId}/members/${memberId}`);
  }

  // Invitation endpoints
  async getInvitations(): Promise<Invitation[]> {
    const response: AxiosResponse<Invitation[]> = await this.api.get('/invitations');
    return response.data;
  }

  async getSentInvitations(): Promise<Invitation[]> {
    const response: AxiosResponse<Invitation[]> = await this.api.get('/invitations/sent');
    return response.data;
  }

  async createInvitation(invitationData: CreateInvitationRequest): Promise<Invitation> {
    const response: AxiosResponse<Invitation> = await this.api.post('/invitations', invitationData);
    return response.data;
  }

  async acceptInvitation(invitationId: string): Promise<void> {
    await this.api.post(`/invitations/${invitationId}/accept`);
  }

  async declineInvitation(invitationId: string): Promise<void> {
    await this.api.post(`/invitations/${invitationId}/decline`);
  }

  async cancelInvitation(invitationId: string): Promise<void> {
    await this.api.delete(`/invitations/${invitationId}`);
  }

  // File upload endpoints
  async uploadFile(file: File, groupId?: string): Promise<UploadedFile> {
    const formData = new FormData();
    formData.append('file', file);
    if (groupId) {
      formData.append('group_id', groupId);
    }

    const response: AxiosResponse<UploadedFile> = await this.api.post('/uploads', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  async getGroupFiles(groupId: string): Promise<UploadedFile[]> {
    const response: AxiosResponse<UploadedFile[]> = await this.api.get(`/uploads/group/${groupId}`);
    return response.data;
  }

  async getUserFiles(): Promise<UploadedFile[]> {
    const response: AxiosResponse<UploadedFile[]> = await this.api.get('/uploads/user');
    return response.data;
  }

  async deleteFile(fileId: string): Promise<void> {
    await this.api.delete(`/uploads/${fileId}`);
  }

  // Search endpoints
  async searchGroups(query: string, filters?: any): Promise<PaginatedResponse<Group>> {
    const response: AxiosResponse<PaginatedResponse<Group>> = await this.api.get('/groups/search', {
      params: { q: query, ...filters }
    });
    return response.data;
  }

  async searchUsers(query: string): Promise<User[]> {
    const response: AxiosResponse<User[]> = await this.api.get('/users/search', {
      params: { q: query }
    });
    return response.data;
  }
}

export const apiService = new ApiService();
export default apiService;
