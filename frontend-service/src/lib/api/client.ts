import { config } from '@/config/env';
import type {
  AuthResponse,
  ConversationDetailResponse,
  ConversationSummary,
  CompleteLessonResult,
  CourseDetail,
  CourseIngestResponse,
  CourseSummary,
  CourseUploadResponse,
  CreateCoursePayload,
  CreateCourseResult,
  CreateServicePayload,
  DocumentDetailResponse,
  EnrollResult,
  FeedbackRequest,
  FeedbackResponse,
  HealthResponse,
  KnowledgeCheckResult,
  KnowledgeFileInfo,
  KnowledgeIngestResponse,
  KnowledgeUploadResponse,
  LessonDetail,
  LessonDoubt,
  LoginRequest,
  Microservice,
  ModelsResponse,
  PendingCourseInfo,
  QueryRequest,
  QueryResponse,
  ShareResponse,
  SharedConversationDetailResponse,
  SignupRequest,
  SourceCitation,
  User,
} from '@/types';

export interface QueryStreamCallbacks {
  onMetadata?: (meta: {
    conversation_id: string;
    message_id: string;
    sources: SourceCitation[];
    service: string;
    provider: string;
    model: string;
    forked?: boolean;
    forked_from?: string | null;
  }) => void;
  onChunk: (chunk: string) => void;
  onDone?: (done: {
    latency_ms: number;
    message_id: string;
    conversation_id?: string;
    complete: boolean;
  }) => void;
  onError?: (err: string) => void;
}

export interface DoubtStreamCallbacks {
  onMetadata?: (meta: {
    doubt_id: string;
    sources: SourceCitation[];
    model: string;
  }) => void;
  onChunk: (chunk: string) => void;
  onDone?: (done: {
    doubt: LessonDoubt;
    latency_ms: number;
    complete: boolean;
  }) => void;
  onError?: (err: string) => void;
}

export interface LessonStreamCallbacks {
  onMetadata?: (meta: {
    course_id: string;
    lesson_id: string;
    lesson_index: number;
    title: string;
    summary: string;
    takeaways?: string[];
    sources: SourceCitation[];
    knowledge_check?: any;
    knowledge_checks?: any[];
    doubts: LessonDoubt[];
    is_completed: boolean;
    model: string;
    is_cached: boolean;
  }) => void;
  onChunk: (chunk: string) => void;
  onDone?: (done: {
    takeaways?: string[];
    clean_content?: string;
    latency_ms: number;
    complete: boolean;
  }) => void;
  onError?: (err: string) => void;
}



export class ApiError extends Error {
  code: string;
  requestId?: string;
  status: number;
  details?: Record<string, any>;

  constructor(status: number, message: string, code = 'API_ERROR', requestId?: string, details?: Record<string, any>) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.requestId = requestId;
    this.details = details;
  }
}

/**
 * Base API Client for FC Central Engineering Intelligence Platform.
 * All HTTP communication with backend-service routes through here.
 */
export class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string = config.apiBaseUrl) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
  }

  setToken(token: string | null): void {
    this.token = token;
  }

  getToken(): string | null {
    return this.token;
  }

  getApiUrl(endpoint: string): string {
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    return `${this.baseUrl}${cleanEndpoint}`;
  }

  async fetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = this.getApiUrl(endpoint);
    const headers = new Headers(options.headers || {});

    if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }

    if (this.token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${this.token}`);
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    const requestId = response.headers.get('X-Request-ID') || undefined;


    if (!response.ok) {
      try {
        const errorJson = await response.json();
        let message = errorJson.message;

        // If Pydantic field validation errors exist, extract the first human-readable description
        if (errorJson.details?.errors && Array.isArray(errorJson.details.errors) && errorJson.details.errors.length > 0) {
          const firstErr = errorJson.details.errors[0];
          const field = Array.isArray(firstErr.loc) ? firstErr.loc[firstErr.loc.length - 1] : undefined;
          const msg = firstErr.msg;
          if (field && msg) {
            message = `${String(field).charAt(0).toUpperCase() + String(field).slice(1)}: ${msg}`;
          } else if (msg) {
            message = msg;
          }
        }

        if (!message) {
          if (response.status === 401) {
            message = 'Invalid email or password.';
          } else if (response.status === 403) {
            message = 'Access forbidden.';
          } else {
            message = `Request failed with status ${response.status}`;
          }
        }

        throw new ApiError(
          response.status,
          message,
          errorJson.code || 'HTTP_ERROR',
          errorJson.request_id || requestId,
          errorJson.details
        );
      } catch (e) {
        if (e instanceof ApiError) throw e;
        const errorText = await response.text().catch(() => 'Unknown server error');
        throw new ApiError(response.status, errorText, 'HTTP_ERROR', requestId);
      }
    }

    return response.json() as Promise<T>;
  }

  private async streamFetch(
    endpoint: string,
    options: RequestInit,
    onMessage: (data: any) => void
  ): Promise<void> {
    const url = this.getApiUrl(endpoint);
    const headers = new Headers(options.headers || {});

    if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }

    if (this.token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${this.token}`);
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    const requestId = response.headers.get('X-Request-ID') || undefined;

    if (!response.ok) {
      try {
        const errorJson = await response.json();
        throw new ApiError(
          response.status,
          errorJson.message || `Request failed with status ${response.status}`,
          errorJson.code || 'HTTP_ERROR',
          errorJson.request_id || requestId,
          errorJson.details
        );
      } catch (e) {
        if (e instanceof ApiError) throw e;
        const errorText = await response.text().catch(() => 'Unknown server error');
        throw new ApiError(response.status, errorText, 'HTTP_ERROR', requestId);
      }
    }

    if (!response.body) {
      throw new Error('ReadableStream not supported in this environment');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data: ')) {
          const raw = trimmed.slice(6);
          try {
            const parsed = JSON.parse(raw);
            onMessage(parsed);
          } catch (e) {
            console.error('Failed to parse SSE event:', raw, e);
          }
        }
      }
    }

    if (buffer.trim().startsWith('data: ')) {
      try {
        const parsed = JSON.parse(buffer.trim().slice(6));
        onMessage(parsed);
      } catch {}
    }
  }

  /**
   * Health check utility to test connectivity to backend
   */
  async checkHealth(): Promise<HealthResponse> {
    return this.fetch<HealthResponse>('/api/v1/health');
  }

  /**
   * Execute an engineering intelligence query against the RAG knowledge base (non-streaming fallback)
   */
  async query(payload: QueryRequest): Promise<QueryResponse> {
    return this.fetch<QueryResponse>('/api/v1/query', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  /**
   * Execute streaming engineering intelligence query via Server-Sent Events (SSE)
   */
  async queryStream(payload: QueryRequest, callbacks: QueryStreamCallbacks): Promise<void> {
    await this.streamFetch(
      '/api/v1/query/stream',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      (event) => {
        if (event.type === 'metadata' && callbacks.onMetadata) {
          callbacks.onMetadata(event);
        } else if (event.type === 'chunk' && callbacks.onChunk) {
          callbacks.onChunk(event.text);
        } else if (event.type === 'done' && callbacks.onDone) {
          callbacks.onDone(event);
        } else if (event.type === 'error' && callbacks.onError) {
          callbacks.onError(event.error);
        }
      }
    );
  }


  /**
   * Submit developer feedback (positive/negative + comment) on an answer
   */
  async submitFeedback(payload: FeedbackRequest): Promise<FeedbackResponse> {
    return this.fetch<FeedbackResponse>('/api/v1/feedback', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  /**
   * Upload a microservice documentation file (.md or .pdf) to staging (no ingestion triggered)
   */
  async uploadKnowledgeFile(service: string, file: File): Promise<KnowledgeUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('service', service);

    return this.fetch<KnowledgeUploadResponse>('/api/v1/knowledge/upload', {
      method: 'POST',
      body: formData,
    });
  }

  /**
   * List all documentation files (pending review and ingested) for a microservice
   */
  async listKnowledgeFiles(service: string): Promise<KnowledgeFileInfo[]> {
    const params = new URLSearchParams({ service });
    return this.fetch<KnowledgeFileInfo[]>(`/api/v1/knowledge/files?${params.toString()}`);
  }

  /**
   * Trigger semantic chunking, embedding, and vector persistence for a microservice (Maintainer action)
   */
  async triggerKnowledgeIngestion(
    service: string,
    sourcePath?: string | null
  ): Promise<KnowledgeIngestResponse> {
    return this.fetch<KnowledgeIngestResponse>('/api/v1/knowledge', {
      method: 'POST',
      body: JSON.stringify({
        service,
        source_path: sourcePath || null,
      }),
    });
  }

  /**
   * Purge existing Qdrant points for this microservice and re-index all staged files from scratch
   */
  async reindexKnowledge(service: string): Promise<KnowledgeIngestResponse> {
    return this.fetch<KnowledgeIngestResponse>('/api/v1/knowledge/reindex', {
      method: 'POST',
      body: JSON.stringify({
        service,
      }),
    });
  }


  /**
   * Upload a Knowledge Cafe course package (.zip archive) to staging (no ingestion triggered)
   */
  async uploadCourseZip(file: File): Promise<CourseUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    return this.fetch<CourseUploadResponse>('/api/v1/knowledge/course/upload', {
      method: 'POST',
      body: formData,
    });
  }

  /**
   * List all Knowledge Cafe courses currently staged under pending review
   */
  async listPendingCourses(): Promise<PendingCourseInfo[]> {
    return this.fetch<PendingCourseInfo[]>('/api/v1/knowledge/course/pending');
  }

  /**
   * Promote and index a staged Knowledge Cafe course into Qdrant vector store
   */
  async triggerCourseIngestion(courseId: string): Promise<CourseIngestResponse> {
    return this.fetch<CourseIngestResponse>('/api/v1/knowledge/course/ingest', {
      method: 'POST',
      body: JSON.stringify({ course_id: courseId }),
    });
  }

  /**
   * Retrieve full source documentation file content safely
   */
  async getDocument(service: string, file: string): Promise<DocumentDetailResponse> {
    const params = new URLSearchParams({ service, file });
    return this.fetch<DocumentDetailResponse>(`/api/v1/documents?${params.toString()}`);
  }

  /**
   * Retrieve full conversation history by conversation ID
   */
  async getConversation(conversationId: string): Promise<ConversationDetailResponse> {
    return this.fetch<ConversationDetailResponse>(`/api/v1/conversations/${encodeURIComponent(conversationId)}`);
  }

  /**
   * List recent conversations, optionally filtered by service
   */
  async listConversations(service?: string, limit = 20): Promise<ConversationSummary[]> {
    const params = new URLSearchParams();
    if (service) params.append('service', service);
    params.append('limit', limit.toString());
    return this.fetch<ConversationSummary[]>(`/api/v1/conversations?${params.toString()}`);
  }

  /**
   * List available microservices discovered by the backend
   */
  async listServices(): Promise<Microservice[]> {
    return this.fetch<Microservice[]>('/api/v1/services');
  }

  /**
   * Register a new microservice context
   */
  async createService(payload: CreateServicePayload): Promise<Microservice> {
    return this.fetch<Microservice>('/api/v1/services', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }


  /**
   * List configured LLM models available on the backend
   */
  async listModels(): Promise<ModelsResponse> {
    return this.fetch<ModelsResponse>('/api/v1/models');
  }

  /**
   * Register a new user account
   */
  async signup(payload: SignupRequest): Promise<AuthResponse> {
    const res = await this.fetch<AuthResponse>('/api/v1/auth/signup', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (res.access_token) {
      this.setToken(res.access_token);
    }
    return res;
  }

  /**
   * Login with email and password
   */
  async login(payload: LoginRequest): Promise<AuthResponse> {
    const res = await this.fetch<AuthResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (res.access_token) {
      this.setToken(res.access_token);
    }
    return res;
  }

  /**
   * Fetch current authenticated user profile
   */
  async getCurrentUser(): Promise<User> {
    return this.fetch<User>('/api/v1/auth/me');
  }

  /**
   * Generate or retrieve a shareable UUID token for an active conversation
   */
  async shareConversation(conversationId: string): Promise<ShareResponse> {
    return this.fetch<ShareResponse>(`/api/v1/conversations/${conversationId}/share`, {
      method: 'POST',
    });
  }

  /**
   * Retrieve a shared conversation and citations (requires user authentication)
   */
  async getSharedConversation(shareToken: string): Promise<SharedConversationDetailResponse> {
    return this.fetch<SharedConversationDetailResponse>(`/api/v1/shared/${shareToken}`);
  }

  /**
   * Logout user and clear local token
   */
  /**
   * Logout user and clear local token
   */
  async logout(): Promise<void> {
    try {
      if (this.token) {
        await this.fetch('/api/v1/auth/logout', { method: 'POST' });
      }
    } catch {
      // Ignore network errors on logout
    } finally {
      this.setToken(null);
    }
  }

  // ==========================================
  // Knowledge Cafe E-Learning & KT APIs
  // ==========================================

  /**
   * List all creator-defined courses with active user enrollment progress
   */
  async listCourses(group?: string): Promise<CourseSummary[]> {
    const query = group ? `?group=${encodeURIComponent(group)}` : '';
    return this.fetch<CourseSummary[]>(`/api/v1/kt/courses${query}`);
  }

  /**
   * Author and publish a new Knowledge Cafe course & quiz
   */
  async createCourse(payload: CreateCoursePayload): Promise<CreateCourseResult> {
    return this.fetch<CreateCourseResult>('/api/v1/kt/courses', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }


  /**
   * Retrieve full course curriculum and lesson sequence from course-structure.md
   */
  async getCourse(courseId: string): Promise<CourseDetail> {
    return this.fetch<CourseDetail>(`/api/v1/kt/courses/${encodeURIComponent(courseId)}`);
  }

  /**
   * Enroll in or resume an existing course session
   */
  async enrollInCourse(courseId: string): Promise<EnrollResult> {
    return this.fetch<EnrollResult>(`/api/v1/kt/courses/${encodeURIComponent(courseId)}/enroll`, {
      method: 'POST',
    });
  }

  /**
   * Restart a course from Lesson 1, resetting completed lessons and progress
   */
  async restartCourse(courseId: string): Promise<EnrollResult> {
    return this.fetch<EnrollResult>(`/api/v1/kt/courses/${encodeURIComponent(courseId)}/restart`, {
      method: 'POST',
    });
  }

  /**
   * Retrieve or synthesize a lesson using its dedicated context files (non-streaming fallback)
   */
  async getLesson(courseId: string, lessonId: string, model?: string): Promise<LessonDetail> {
    const params = new URLSearchParams();
    if (model) params.append('model', model);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return this.fetch<LessonDetail>(
      `/api/v1/kt/courses/${encodeURIComponent(courseId)}/lessons/${encodeURIComponent(lessonId)}${qs}`
    );
  }

  /**
   * Stream progressive lesson synthesis via SSE
   */
  async getLessonContentStream(
    courseId: string,
    lessonId: string,
    model: string | undefined,
    callbacks: LessonStreamCallbacks
  ): Promise<void> {
    const qs = model ? `?model=${encodeURIComponent(model)}` : '';
    await this.streamFetch(
      `/api/v1/kt/courses/${encodeURIComponent(courseId)}/lessons/${encodeURIComponent(lessonId)}/stream${qs}`,
      { method: 'GET' },
      (event) => {
        if (event.type === 'metadata' && callbacks.onMetadata) {
          callbacks.onMetadata(event);
        } else if (event.type === 'chunk' && callbacks.onChunk) {
          callbacks.onChunk(event.text);
        } else if (event.type === 'done' && callbacks.onDone) {
          callbacks.onDone(event);
        } else if (event.type === 'error' && callbacks.onError) {
          callbacks.onError(event.error);
        }
      }
    );
  }

  /**
   * Mark a lesson complete and unlock the next lesson in the curriculum
   */
  async completeLesson(courseId: string, lessonId: string): Promise<CompleteLessonResult> {
    return this.fetch<CompleteLessonResult>(
      `/api/v1/kt/courses/${encodeURIComponent(courseId)}/lessons/${encodeURIComponent(lessonId)}/complete`,
      { method: 'POST' }
    );
  }

  /**
   * Ask an in-lesson question grounded in dedicated course context (non-streaming fallback)
   */
  async askLessonDoubt(
    courseId: string,
    lessonId: string,
    question: string,
    model?: string
  ): Promise<LessonDoubt> {
    return this.fetch<LessonDoubt>(
      `/api/v1/kt/courses/${encodeURIComponent(courseId)}/lessons/${encodeURIComponent(lessonId)}/doubts`,
      {
        method: 'POST',
        body: JSON.stringify({ question, model: model || null }),
      }
    );
  }

  /**
   * Ask in-lesson doubt with real-time SSE streaming
   */
  async askLessonDoubtStream(
    courseId: string,
    lessonId: string,
    question: string,
    model: string | undefined,
    callbacks: DoubtStreamCallbacks
  ): Promise<void> {
    await this.streamFetch(
      `/api/v1/kt/courses/${encodeURIComponent(courseId)}/lessons/${encodeURIComponent(lessonId)}/doubts/stream`,
      {
        method: 'POST',
        body: JSON.stringify({ question, model: model || null }),
      },
      (event) => {
        if (event.type === 'metadata' && callbacks.onMetadata) {
          callbacks.onMetadata(event);
        } else if (event.type === 'chunk' && callbacks.onChunk) {
          callbacks.onChunk(event.text);
        } else if (event.type === 'done' && callbacks.onDone) {
          callbacks.onDone(event);
        } else if (event.type === 'error' && callbacks.onError) {
          callbacks.onError(event.error);
        }
      }
    );
  }


  /**
   * Submit an answer to an interactive knowledge check
   */
  async submitKnowledgeCheck(
    courseId: string,
    lessonId: string,
    selectedOptionIndex?: number,
    questionIndex: number = 0,
    answers?: number[]
  ): Promise<KnowledgeCheckResult> {
    return this.fetch<KnowledgeCheckResult>(
      `/api/v1/kt/courses/${encodeURIComponent(courseId)}/lessons/${encodeURIComponent(lessonId)}/check`,
      {
        method: 'POST',
        body: JSON.stringify({
          selected_option_index: selectedOptionIndex,
          question_index: questionIndex,
          answers: answers,
        }),
      }
    );
  }

  /**
   * Retrieve full course context document for 'View Source'
   */
  async getCourseDocument(courseId: string, file: string): Promise<DocumentDetailResponse> {
    const params = new URLSearchParams({ file });
    return this.fetch<DocumentDetailResponse>(
      `/api/v1/kt/courses/${encodeURIComponent(courseId)}/documents?${params.toString()}`
    );
  }

  /**
   * Reset Knowledge Cafe progress for current user or all users
   */
  async resetKTProgress(options?: { courseId?: string; allUsers?: boolean; clearDoubts?: boolean; clearCache?: boolean }): Promise<any> {
    const params = new URLSearchParams();
    if (options?.courseId) params.append('course_id', options.courseId);
    if (options?.allUsers) params.append('all_users', 'true');
    if (options?.clearDoubts !== undefined) params.append('clear_doubts', String(options.clearDoubts));
    if (options?.clearCache !== undefined) params.append('clear_cache', String(options.clearCache));
    const qs = params.toString() ? `?${params.toString()}` : '';
    return this.fetch<any>(`/api/v1/kt/progress/reset${qs}`, {
      method: 'POST',
    });
  }

  /**
   * Purge synthesized lesson cache so materials are regenerated afresh
   */
  async clearKTCache(courseId?: string): Promise<any> {
    const params = new URLSearchParams();
    if (courseId) params.append('course_id', courseId);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return this.fetch<any>(`/api/v1/kt/cache/clear${qs}`, {
      method: 'POST',
    });
  }


}

export const apiClient = new ApiClient();
export default apiClient;

