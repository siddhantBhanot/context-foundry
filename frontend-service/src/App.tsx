import { useEffect, useRef, useState } from 'react';
import {
  Activity,
  ArrowUp,
  ChevronDown,
  Code2,
  GitBranch,
  GitMerge,
  GraduationCap,
  History,
  Layers,
  Loader2,
  LogOut,
  MessageSquare,
  RotateCcw,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Share2,
  Cpu,
  UploadCloud,
} from 'lucide-react';

import { MarkdownRenderer } from '@/components/chat/MarkdownRenderer';
import { SourceCitationList } from '@/components/chat/SourceCitationList';
import { FeedbackControls } from '@/components/chat/FeedbackControls';
import { IngestionModal } from '@/components/chat/IngestionModal';
import { ConversationHistoryDrawer } from '@/components/chat/ConversationHistoryDrawer';
import { ShareModal } from '@/components/chat/ShareModal';
import { DocumentViewerModal } from '@/components/chat/DocumentViewerModal';
import { KnowledgeCafeView } from '@/components/kt/KnowledgeCafeView';
import { AuthProvider, useAuth } from '@/lib/auth/AuthContext';
import { AuthScreen } from '@/components/auth/AuthScreen';
import apiClient, { ApiError } from '@/lib/api/client';
import type { ChatMessage, Microservice, ModelInfo } from '@/types';
import { ContextFoundryLogo } from '@/components/brand/ContextFoundryLogo';


const DEFAULT_SERVICES: Microservice[] = [
  {
    id: 'income-assessment-service',
    name: 'income-assessment-service',
    description: 'Income assessment rules engine & eligibility calculations',
    has_indexed_data: true,
  },
  {
    id: 'loan-origination-service',
    name: 'loan-origination-service',
    description: 'Loan application lifecycle & underwriting workflows',
    has_indexed_data: false,
  },
  {
    id: 'kyc-verification-service',
    name: 'kyc-verification-service',
    description: 'Identity verification & document assessment',
    has_indexed_data: false,
  },
];

const FEATURE_CARDS = [
  {
    id: 'apis',
    icon: Code2,
    title: 'APIs',
    description: 'Endpoints, params, auth, and response schemas across every service.',
    query: 'What are the main endpoints and auth schemas for this service?',
  },
  {
    id: 'business-logic',
    icon: GitBranch,
    title: 'Business logic',
    description: 'How rules, eligibility, and calculations are evaluated under the hood.',
    query: 'What is the business handler for FOUR_WHEELER_PERSONAL and what endpoint does it expose?',
  },
  {
    id: 'request-flows',
    icon: GitMerge,
    title: 'Request flows',
    description: 'Trace a request end-to-end, including retries, queues, and callbacks.',
    query: 'What is the usual request flow for income-assessment-service?',
  },
  {
    id: 'integrations',
    icon: Layers,
    title: 'Integrations',
    description: 'Third-party connections, webhooks, and cross-service dependencies.',
    query: 'What is Zenith and what is it used for?',
  },
];

function DashboardApp() {
  const { user, isAuthenticated, isLoading: isAuthLoading, logout } = useAuth();
  const [services, setServices] = useState<Microservice[]>(DEFAULT_SERVICES);
  const [selectedService, setSelectedService] = useState<string>(DEFAULT_SERVICES[0].id);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [queryInput, setQueryInput] = useState<string>('');
  const [isChatActive, setIsChatActive] = useState<boolean>(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isIngestionModalOpen, setIsIngestionModalOpen] = useState<boolean>(false);
  const [isHistoryDrawerOpen, setIsHistoryDrawerOpen] = useState<boolean>(false);
  const [isShareModalOpen, setIsShareModalOpen] = useState<boolean>(false);
  const [shareToken, setShareToken] = useState<string | null>(null);
  const [isSharingLoading, setIsSharingLoading] = useState<boolean>(false);
  const [activeSharedToken, setActiveSharedToken] = useState<string | null>(() => {
    if (typeof window !== 'undefined') {
      return new URLSearchParams(window.location.search).get('share');
    }
    return null;
  });
  const [sharedInfo, setSharedInfo] = useState<{
    isOwner: boolean;
    title?: string | null;
    forkedFrom?: string | null;
  } | null>(null);
  const [forkNotification, setForkNotification] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<{ message: string; requestId?: string } | null>(null);
  const [activeMode, setActiveMode] = useState<'chat' | 'knowledge-cafe'>('chat');
  const [activeSourceModal, setActiveSourceModal] = useState<{
    isOpen: boolean;
    file: string;
    service: string;
  }>({ isOpen: false, file: '', service: 'income-assessment-service' });


  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isChatActive) {
      scrollToBottom();
    }
  }, [messages, isChatActive, isLoading]);

  // Initial health check, service discovery & model loading
  useEffect(() => {
    const checkConnection = async () => {
      try {
        await apiClient.checkHealth();
      } catch {
        // Backend offline or unreachable
      }

      try {
        const remoteServices = await apiClient.listServices();
        if (remoteServices && remoteServices.length > 0) {
          setServices(remoteServices);
        }
      } catch {
        // Keep default services if fetch fails
      }

      try {
        const modelsData = await apiClient.listModels();
        if (modelsData && modelsData.models && modelsData.models.length > 0) {
          setModels(modelsData.models);
          setSelectedModel((prev) => {
            if (prev && modelsData.models.some((m) => m.id === prev)) return prev;
            return modelsData.default_model || modelsData.models[0].id;
          });
        }
      } catch {
        // Keep models if fetch fails
      }
    };

    checkConnection();
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  // Auto-load shared conversation when authenticated and share token is present in URL
  useEffect(() => {
    if (!isAuthenticated || !activeSharedToken) return;

    const loadSharedConversation = async () => {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const data = await apiClient.getSharedConversation(activeSharedToken);
        setCurrentConversationId(data.id);
        setSelectedService(data.service);
        setShareToken(data.share_token);
        setSharedInfo({
          isOwner: data.is_owner,
          title: data.title,
          forkedFrom: data.forked_from,
        });

        const loadedMessages: ChatMessage[] = data.messages.map((m) => ({
          id: m.id,
          conversationId: data.id,
          role: m.role as 'user' | 'assistant' | 'system',
          content: m.content,
          timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          status: 'complete',
          sources: m.sources,
        }));

        setMessages(loadedMessages);
        setIsChatActive(true);
      } catch (err: any) {
        console.error('Failed to load shared conversation:', err);
        setErrorMessage({ message: 'Shared conversation not found or link has expired.' });
      } finally {
        setIsLoading(false);
      }
    };

    loadSharedConversation();
  }, [isAuthenticated, activeSharedToken]);

  const handleStartChat = async (queryText?: string) => {
    const text = (queryText || queryInput).trim();
    if (!text || isLoading) return;

    setErrorMessage(null);

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      conversationId: currentConversationId || undefined,
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    const assistantTempId = `assistant-${Date.now()}`;
    const initialAssistantMsg: ChatMessage = {
      id: assistantTempId,
      conversationId: currentConversationId || undefined,
      role: 'assistant',
      content: '',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      status: 'streaming',
      model: selectedModel || undefined,
    };

    setMessages((prev) => [...prev, userMessage, initialAssistantMsg]);
    setIsChatActive(true);
    setQueryInput('');
    setIsLoading(true);

    try {
      await apiClient.queryStream(
        {
          query: text,
          conversation_id: currentConversationId,
          share_token: activeSharedToken || undefined,
          service: selectedService,
          model: selectedModel || undefined,
          top_k: 5,
        },
        {
          onMetadata: (meta) => {
            setIsLoading(false);
            if (meta.forked) {
              setCurrentConversationId(meta.conversation_id);
              setActiveSharedToken(null);
              setSharedInfo(null);
              setShareToken(null);
              if (typeof window !== 'undefined') {
                window.history.replaceState({}, document.title, window.location.pathname);
              }
              setForkNotification('Conversation branched! You are now continuing on your own personal fork.');
              setTimeout(() => setForkNotification(null), 6000);
            } else if (meta.conversation_id) {
              setCurrentConversationId(meta.conversation_id);
            }

            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantTempId
                  ? {
                      ...msg,
                      id: meta.message_id || msg.id,
                      conversationId: meta.conversation_id,
                      sources: meta.sources,
                      provider: meta.provider,
                      model: meta.model,
                    }
                  : msg
              )
            );
          },
          onChunk: (chunk) => {
            setIsLoading(false);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantTempId || msg.status === 'streaming'
                  ? { ...msg, content: msg.content + chunk }
                  : msg
              )
            );
          },
          onDone: (done) => {
            setIsLoading(false);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantTempId || msg.status === 'streaming'
                  ? {
                      ...msg,
                      id: done.message_id || msg.id,
                      status: 'complete',
                      latencyMs: done.latency_ms,
                    }
                  : msg
              )
            );
          },
          onError: (err) => {
            setIsLoading(false);
            setErrorMessage({ message: err });
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantTempId || msg.status === 'streaming'
                  ? { ...msg, status: 'error' }
                  : msg
              )
            );
          },
        }
      );
    } catch (err: any) {
      console.error('Query error:', err);
      let errorDesc = 'Failed to get response from engineering intelligence service.';
      let reqId: string | undefined;

      if (err instanceof ApiError) {
        errorDesc = err.message;
        reqId = err.requestId;
      } else if (err.message) {
        errorDesc = err.message;
      }

      setErrorMessage({ message: errorDesc, requestId: reqId });

      const errorBubble: ChatMessage = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `⚠️ **Unable to complete response:** ${errorDesc}\n\n*Please ensure the backend service and Qdrant/Groq are reachable.*`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        status: 'error',
      };
      setMessages((prev) => [...prev, errorBubble]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpenShare = async () => {
    if (!currentConversationId) return;
    setIsShareModalOpen(true);
    setIsSharingLoading(true);
    try {
      const res = await apiClient.shareConversation(currentConversationId);
      setShareToken(res.share_token);
    } catch (err: any) {
      console.error('Failed to generate share link:', err);
      setErrorMessage({ message: err.message || 'Failed to generate share link.' });
    } finally {
      setIsSharingLoading(false);
    }
  };

  const handleResetHome = () => {
    setIsChatActive(false);
    setMessages([]);
    setCurrentConversationId(null);
    setQueryInput('');
    setErrorMessage(null);
    setActiveSharedToken(null);
    setSharedInfo(null);
    setShareToken(null);
    setForkNotification(null);
    if (typeof window !== 'undefined') {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  };

  const handleSelectConversation = async (conversationId: string) => {
    setIsLoading(true);
    setErrorMessage(null);
    setActiveSharedToken(null);
    setSharedInfo(null);
    setShareToken(null);
    setForkNotification(null);
    if (typeof window !== 'undefined') {
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    try {
      const detail = await apiClient.getConversation(conversationId);
      setCurrentConversationId(detail.id);
      setSelectedService(detail.service);

      const loadedMessages: ChatMessage[] = detail.messages.map((m) => ({
        id: m.id,
        conversationId: detail.id,
        role: m.role as 'user' | 'assistant' | 'system',
        content: m.content,
        timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        status: 'complete',
        sources: m.sources,
      }));

      setMessages(loadedMessages);
      setIsChatActive(true);
    } catch (err: any) {
      console.error('Failed to load conversation:', err);
      setErrorMessage({ message: 'Failed to load conversation history.' });
    } finally {
      setIsLoading(false);
    }
  };

  if (isAuthLoading) {

    return (
      <div className="min-h-screen bg-[#edf3f8] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-[#f05a28]/20 border-t-[#f05a28] rounded-full animate-spin" />
          <span className="text-xs text-slate-500 font-semibold tracking-wider uppercase">Validating session...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <AuthScreen />;
  }

  return (

    <div className="min-h-screen bg-[#edf3f8] flex flex-col justify-between px-3 sm:px-5 md:px-8 py-3 sm:py-4 md:py-6 font-sans antialiased text-slate-800">
      {/* Outer White Card styled container */}
      <div className="w-full max-w-7xl mx-auto bg-white rounded-[24px] md:rounded-[36px] shadow-sm border border-slate-100 flex flex-col min-h-[92vh] md:min-h-[94vh] overflow-hidden">
        
        {/* Persistent Top Header */}
        <header className="px-6 md:px-10 py-5 flex items-center justify-between border-b border-slate-100 bg-white shrink-0">
          {/* ContextFoundry Logo on Left */}
          <div className="flex items-center gap-2.5">
            <button
              onClick={handleResetHome}
              className="flex items-center text-left group cursor-pointer focus:outline-none"
              title="Return to Home"
            >
              <ContextFoundryLogo />
            </button>
            <span className="text-[10px] font-bold tracking-wider uppercase hidden xl:inline-block border-l border-slate-200 pl-2.5 self-center py-0.5 text-slate-400">
              Engineering Intelligence
            </span>
          </div>

          {/* Center Mode Switcher: Dev Chat & Knowledge Cafe */}
          <div className="flex items-center bg-slate-100/90 p-1.5 rounded-full border border-slate-200/80 shadow-2xs gap-1">
            <button
              onClick={() => setActiveMode('chat')}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                activeMode === 'chat'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              <span>Dev Chat</span>
            </button>

            <button
              onClick={() => setActiveMode('knowledge-cafe')}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                activeMode === 'knowledge-cafe'
                  ? 'bg-[#f05a28] text-white shadow-xs'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              <GraduationCap className="w-4 h-4" />
              <span>Knowledge Cafe</span>
              <span
                className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase tracking-wider ${
                  activeMode === 'knowledge-cafe'
                    ? 'bg-white/25 text-white'
                    : 'bg-orange-100 text-[#f05a28]'
                }`}
              >
                KT
              </span>
            </button>
          </div>

          {/* Right Actions: Knowledge Ingest, History, New Chat, User */}
          <div className="flex items-center gap-2.5 sm:gap-3.5">
            {/* Knowledge Ingestion Modal Trigger */}
            <button
              onClick={() => setIsIngestionModalOpen(true)}
              className="flex items-center gap-2 px-3.5 py-2 rounded-full text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer"
              title="Upload and stage documentation or courses"
            >
              <UploadCloud className="w-4 h-4 text-[#f05a28]" />
              <span className="hidden md:inline">Upload Docs</span>
            </button>

            {/* Conversation History Drawer Trigger */}
            <button
              onClick={() => setIsHistoryDrawerOpen(true)}
              className="flex items-center gap-2 px-3.5 py-2 rounded-full text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer"
              title="View conversation history"
            >
              <History className="w-4 h-4 text-slate-500" />
              <span className="hidden md:inline">History</span>
            </button>

            {/* Share Button when conversation is active */}
            {currentConversationId && isChatActive && (
              <button
                onClick={handleOpenShare}
                className="flex items-center gap-2 px-3.5 py-2 rounded-full text-xs font-semibold text-[#f05a28] bg-orange-50 hover:bg-orange-100 transition-colors cursor-pointer shadow-2xs"
                title="Share this conversation"
              >
                <Share2 className="w-4 h-4" />
                <span className="hidden sm:inline">Share</span>
              </button>
            )}

            {isChatActive && (
              <button
                onClick={handleResetHome}
                className="flex items-center gap-2 px-3.5 py-2 rounded-full text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer"
                title="Start a new conversation"
              >
                <RotateCcw className="w-4 h-4" />
                <span className="hidden sm:inline">New Chat</span>
              </button>
            )}

            {/* User Identity & Logout */}
            <div className="flex items-center gap-2.5 pl-3 sm:pl-4 border-l border-slate-200 ml-1">
              <div
                className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200/80 text-xs"
                title={`Signed in as ${user?.email} (Engineering Team)`}
              >
                <span className="w-5 h-5 rounded-full bg-[#f05a28] text-white font-bold text-[10px] flex items-center justify-center uppercase shadow-xs">
                  {user?.name ? user.name.charAt(0) : 'E'}
                </span>
                <div className="flex flex-col text-left">
                  <span className="font-semibold text-slate-700 max-w-[120px] truncate hidden md:inline leading-tight">
                    {user?.name || user?.email}
                  </span>
                  <span className="text-[9px] font-bold text-slate-400 uppercase hidden md:inline leading-none">
                    {user?.role || 'Engineer'}
                  </span>
                </div>
              </div>

              <button
                type="button"
                onClick={() => {
                  handleResetHome();
                  logout();
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold text-slate-500 hover:text-rose-600 hover:bg-rose-50 transition-all cursor-pointer"
                title="Sign out of Dev Central"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </header>


        {/* Global Error Banner if any */}
        {errorMessage && (
          <div className="bg-rose-50 border-b border-rose-200 px-6 py-2 flex items-center justify-between text-xs text-rose-700">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600" />
              <span>{errorMessage.message}</span>
              {errorMessage.requestId && (
                <span className="font-mono text-[10px] text-rose-500">
                  (Req: {errorMessage.requestId})
                </span>
              )}
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-rose-500 hover:text-rose-800 font-bold cursor-pointer"
            >
              ✕
            </button>
          </div>
        )}

        {/* Dynamic Body: Knowledge Cafe vs Chat / Home Screen */}
        {activeMode === 'knowledge-cafe' ? (
          <KnowledgeCafeView
            selectedModel={selectedModel}
            userRole={user?.role}
            services={services}
            onViewSource={(file, service) => {
              setActiveSourceModal({
                isOpen: true,
                file,
                service: service || selectedService,
              });
            }}
            onExploreInChat={(targetService) => {
              setSelectedService(targetService);
              setActiveMode('chat');
              handleResetHome();
            }}
          />
        ) : !isChatActive ? (
          /* =========================================================================
             1. HOME SCREEN
             ========================================================================= */
          <main className="flex-1 px-6 md:px-12 py-8 md:py-12 flex flex-col justify-center items-center">
            <div className="w-full max-w-2xl mx-auto flex flex-col items-center">
              
              {/* Badge: # Developer knowledge base */}
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 text-slate-600 text-[11px] font-medium border border-slate-200/80 mb-5 shadow-2xs">
                <Sparkles className="w-3 h-3 text-[#f05a28]" />
                <span>Developer knowledge base</span>
              </div>

              {/* Main Heading: Ask anything about your services */}
              <h1 className="text-3xl sm:text-4xl md:text-5xl font-black text-slate-900 tracking-tight text-center leading-[1.15] mb-3">
                Ask anything about <br />
                your services
              </h1>

              {/* Subtitle with bolded keywords */}
              <p className="text-slate-500 text-xs sm:text-sm text-center max-w-lg leading-relaxed mb-8">
                Get instant, grounded answers on <span className="font-semibold text-slate-700">APIs</span>,{' '}
                <span className="font-semibold text-slate-700">business logic</span>,{' '}
                <span className="font-semibold text-slate-700">request flows</span>, and{' '}
                <span className="font-semibold text-slate-700">integrations</span> — straight from your service documentation.
              </p>

              {/* Empty State Banner if no files are ingested for the selected service */}
              {(() => {
                const activeSvc = services.find((s) => s.id === selectedService);
                const hasDocs = activeSvc ? (activeSvc.doc_count !== undefined ? activeSvc.doc_count > 0 : activeSvc.has_indexed_data) : true;
                if (!hasDocs) {
                  return (
                    <div className="w-full mb-5 p-4 rounded-2xl bg-orange-50/90 border border-orange-200/90 text-left flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-2xs">
                      <div className="flex items-start gap-3">
                        <div className="p-2 rounded-xl bg-white text-[#f05a28] shadow-2xs shrink-0 mt-0.5 sm:mt-0">
                          <UploadCloud className="w-5 h-5" />
                        </div>
                        <div>
                          <h4 className="font-bold text-xs text-slate-900">
                            No knowledge indexed yet for <span className="font-mono text-[#f05a28]">{selectedService}</span>
                          </h4>
                          <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">
                            Upload Kotlin source (<code className="font-mono text-slate-700">.kt</code>, <code className="font-mono text-slate-700">.kts</code>), Markdown (<code className="font-mono text-slate-700">.md</code>), PDF (<code className="font-mono text-slate-700">.pdf</code>), or a ZIP archive to ground the AI.
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => setIsIngestionModalOpen(true)}
                        className="px-4 py-2 bg-[#f05a28] hover:bg-[#d94b1c] text-white text-xs font-bold rounded-xl shadow-2xs transition-colors shrink-0 cursor-pointer"
                      >
                        Upload Code & Docs
                      </button>
                    </div>
                  );
                }
                return null;
              })()}

              {/* Central Input Box Container */}
              <div className="w-full bg-white rounded-2xl border border-slate-200 shadow-xs p-4 mb-8 transition-all focus-within:border-slate-300 focus-within:shadow-md">
                {/* Top Row: Context Selectors (SERVICE + MODEL) */}
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-bold text-slate-400 tracking-wider uppercase">
                      SERVICE
                    </span>
                    <div className="relative">
                      <select
                        value={selectedService}
                        onChange={(e) => {
                          if (e.target.value === '__add_new__') {
                            setIsIngestionModalOpen(true);
                          } else {
                            setSelectedService(e.target.value);
                          }
                        }}
                        className="appearance-none bg-slate-100 hover:bg-slate-200/70 text-slate-700 text-xs font-semibold pl-2.5 pr-6 py-1 rounded-lg border border-slate-200/60 focus:outline-none cursor-pointer"
                      >
                        {services.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.name} {s.doc_count !== undefined ? `(${s.doc_count})` : ''}
                          </option>
                        ))}
                        <option value="__add_new__">+ Add Microservice...</option>
                      </select>
                      <ChevronDown className="w-3 h-3 text-slate-400 absolute right-2 top-2 pointer-events-none" />
                    </div>
                  </div>


                  {models.length > 0 && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-bold text-slate-400 tracking-wider uppercase flex items-center gap-1">
                        <Cpu className="w-3 h-3 text-[#f05a28]" />
                        MODEL
                      </span>
                      <div className="relative">
                        <select
                          value={selectedModel}
                          onChange={(e) => setSelectedModel(e.target.value)}
                          className="appearance-none bg-slate-100 hover:bg-slate-200/70 text-slate-700 text-xs font-semibold pl-2.5 pr-6 py-1 rounded-lg border border-slate-200/60 focus:outline-none cursor-pointer"
                        >
                          {models.map((m) => (
                            <option key={m.id} value={m.id}>
                              {m.name} ({m.provider ? m.provider.toUpperCase() : 'LLM'}) {m.is_default ? '(Default)' : ''}
                            </option>
                          ))}
                        </select>
                        <ChevronDown className="w-3 h-3 text-slate-400 absolute right-2 top-2 pointer-events-none" />
                      </div>
                    </div>
                  )}
                </div>

                {/* Middle Row: Text Input */}
                <textarea
                  value={queryInput}
                  onChange={(e) => setQueryInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleStartChat();
                    }
                  }}
                  placeholder={`Ask about ${selectedService}...`}
                  rows={2}
                  disabled={isLoading}
                  className="w-full resize-none bg-transparent text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none py-1"
                />

                {/* Bottom Row: Circular Orange Up-Arrow Send Button */}
                <div className="flex justify-end pt-1">
                  <button
                    onClick={() => handleStartChat()}
                    disabled={!queryInput.trim() || isLoading}
                    type="button"
                    className={`w-7 h-7 rounded-full flex items-center justify-center transition-all cursor-pointer ${
                      queryInput.trim() && !isLoading
                        ? 'bg-[#f05a28] text-white shadow-xs hover:bg-[#d94b1c]'
                        : 'bg-orange-100 text-[#f05a28] hover:bg-[#f05a28] hover:text-white'
                    }`}
                    title="Send message"
                  >
                    {isLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <ArrowUp className="w-4 h-4 stroke-[2.5]" />
                    )}
                  </button>
                </div>
              </div>

              {/* WHAT YOU CAN ASK ABOUT Section Header */}
              <div className="text-[10px] font-bold text-slate-400 tracking-widest uppercase text-center mb-4">
                WHAT YOU CAN ASK ABOUT
              </div>

              {/* 2x2 Feature Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full">
                {FEATURE_CARDS.map((item) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleStartChat(item.query)}
                      className="bg-white hover:bg-slate-50/80 border border-slate-200/90 rounded-2xl p-4 flex items-start gap-3.5 transition-all text-left group cursor-pointer shadow-2xs hover:shadow-xs"
                    >
                      <div className="w-8 h-8 rounded-xl bg-orange-50 group-hover:bg-orange-100 text-[#f05a28] flex items-center justify-center shrink-0 transition-colors">
                        <Icon className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="font-bold text-sm text-slate-900 group-hover:text-[#f05a28] transition-colors">
                          {item.title}
                        </h4>
                        <p className="text-xs text-slate-500 leading-relaxed mt-0.5">
                          {item.description}
                        </p>
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Disclaimer at bottom */}
              <div className="text-center text-[11px] text-slate-400 mt-10 space-y-0.5">
                <p>Answers are grounded live with Qdrant Cloud vectors and Groq inference.</p>
                <p className="text-[10px] text-slate-400">ContextFoundry · Developer Assistant</p>
              </div>

            </div>
          </main>
        ) : (
          /* =========================================================================
             2. CHAT WINDOW
             ========================================================================= */
          <main className="flex-1 flex flex-col justify-between p-4 md:p-8 min-w-0 bg-white">
            
            {/* Scrollable Conversation Stream */}
            <div className="flex-1 overflow-y-auto max-w-3xl mx-auto w-full space-y-6 pb-6 pr-1">
              
              {/* Service header indicator */}
              <div className="flex items-center justify-center gap-2 py-1">
                <span className="text-xs font-semibold text-slate-500 bg-slate-100 px-3 py-1 rounded-full border border-slate-200">
                  Inspecting: <span className="text-[#f05a28] font-mono">{selectedService}</span>
                </span>
                {currentConversationId && (
                  <span className="text-[10px] font-mono text-slate-400 bg-slate-50 px-2 py-1 rounded-full border border-slate-200/60 truncate max-w-[120px]">
                    ID: {currentConversationId.slice(0, 8)}...
                  </span>
                )}
              </div>

              {/* Shared Thread Indicator Banner */}
              {sharedInfo && (
                <div className="p-3.5 rounded-2xl bg-amber-50 border border-amber-200/80 text-amber-950 text-xs flex items-center justify-between gap-3 shadow-xs animate-in fade-in duration-150">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <GitBranch className="w-4 h-4 text-amber-700 shrink-0" />
                    <div className="min-w-0">
                      <span className="font-bold">
                        {sharedInfo.isOwner
                          ? 'Viewing your shared conversation'
                          : 'Viewing shared conversation'}
                      </span>
                      <span className="text-amber-800 text-[11px] block sm:inline sm:ml-1.5 truncate">
                        {sharedInfo.isOwner
                          ? '— anyone with this link can inspect and branch off this thread.'
                          : '— replying will automatically fork this thread into your personal account.'}
                      </span>
                    </div>
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-200/80 text-amber-900 shrink-0">
                    {sharedInfo.isOwner ? 'Shared Link' : 'Fork-on-Reply'}
                  </span>
                </div>
              )}

              {/* Fork Notification Banner */}
              {forkNotification && (
                <div className="p-3 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2 animate-in fade-in shadow-xs">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span className="font-semibold">{forkNotification}</span>
                </div>
              )}

              {messages.map((msg) => (
                <div key={msg.id} className="space-y-2 min-w-0 w-full">
                  {msg.role === 'user' ? (
                    /* User Message Bubble */
                    <div className="flex justify-end min-w-0">
                      <div className="max-w-[85%] min-w-0 rounded-2xl rounded-tr-xs bg-slate-900 px-4 py-2.5 text-xs sm:text-sm text-white shadow-xs break-words [overflow-wrap:anywhere]">
                        {msg.content}
                      </div>
                    </div>
                  ) : (
                    /* Assistant Message Bubble */
                    <div className="flex justify-start min-w-0 w-full">
                      <div className="max-w-[95%] w-full min-w-0 overflow-hidden rounded-2xl rounded-tl-xs bg-[#f8fafc] border border-slate-200 p-5 shadow-xs space-y-3 break-words [overflow-wrap:anywhere]">
                        {/* Assistant message header */}
                        <div className="flex items-center justify-between border-b border-slate-200/80 pb-2.5">
                          <div className="flex items-center gap-2">
                            <div className="w-5 h-5 rounded-md bg-[#f05a28] flex items-center justify-center text-white">
                              <Sparkles className="w-3 h-3" />
                            </div>
                            <span className="text-xs font-bold text-slate-800">
                              Developer Assistant
                            </span>
                          </div>
                          {msg.status === 'streaming' ? (
                            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-orange-700 bg-orange-50 px-2.5 py-0.5 rounded-full border border-orange-200 animate-pulse">
                              <span className="w-2 h-2 rounded-full bg-[#f05a28]" />
                              <span>Streaming Live</span>
                            </div>
                          ) : (
                            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                              <CheckCircle2 className="w-3 h-3 text-[#00b074]" />
                              <span>Verified Grounded</span>
                            </div>
                          )}
                        </div>

                        {/* Markdown & Kotlin syntax highlighter */}
                        <div className="relative">
                          {msg.content ? (
                            <MarkdownRenderer content={msg.content} />
                          ) : (
                            <div className="py-2 text-xs text-slate-400 italic animate-pulse">
                              Synthesizing answer from verified documentation...
                            </div>
                          )}
                          {msg.status === 'streaming' && msg.content && (
                            <span className="inline-block w-1.5 h-3.5 ml-1 bg-[#f05a28] animate-pulse align-middle" />
                          )}
                        </div>

                        {/* Citations if available */}
                        {msg.sources && msg.sources.length > 0 && (
                          <SourceCitationList sources={msg.sources} service={selectedService} />
                        )}

                        {/* Message Quality Feedback Controls */}
                        {msg.conversationId && msg.id && msg.status === 'complete' && (
                          <FeedbackControls
                            messageId={msg.id}
                            conversationId={msg.conversationId}
                            initialRating={msg.feedbackRating}
                          />
                        )}

                        {/* Telemetry Footer */}
                        {msg.latencyMs && (
                          <div className="flex items-center justify-between pt-1 text-[10px] text-slate-400 font-mono">
                            <span className="flex items-center gap-1">
                              <Activity className="w-3 h-3 text-emerald-500" />
                              <span>Latency: {msg.latencyMs.toFixed(0)} ms</span>
                            </span>
                            <span className="flex items-center gap-1" title={`Inference Model: ${msg.model || 'gpt-oss-120b'}`}>
                              <Cpu className="w-3 h-3 text-slate-400" />
                              <span>Model: {msg.model || 'gpt-oss-120b'}</span>
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {/* Generating / Thinking Pulse Indicator (only before first token arrives) */}
              {isLoading && !messages.some((m) => m.status === 'streaming' && m.content.length > 0) && (
                <div className="flex justify-start">
                  <div className="rounded-2xl rounded-tl-xs bg-[#f8fafc] border border-slate-200 px-4 py-3 shadow-xs flex items-center gap-3">
                    <Loader2 className="w-4 h-4 text-[#f05a28] animate-spin" />
                    <span className="text-xs text-slate-600 font-medium">
                      Retrieving neural vectors & generating answer...
                    </span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Shifted Bottom Input Box */}
            <div className="max-w-3xl mx-auto w-full pt-2">
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-3 focus-within:border-slate-300 focus-within:shadow-md transition-all">
                {/* Top Row: Context Selectors (SERVICE + MODEL) */}
                <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-bold text-slate-400 tracking-wider uppercase">
                      SERVICE
                    </span>
                    <div className="relative">
                      <select
                        value={selectedService}
                        onChange={(e) => {
                          if (e.target.value === '__add_new__') {
                            setIsIngestionModalOpen(true);
                          } else {
                            setSelectedService(e.target.value);
                          }
                        }}
                        className="appearance-none bg-slate-100 hover:bg-slate-200/70 text-slate-700 text-xs font-semibold pl-2.5 pr-6 py-1 rounded-lg border border-slate-200/60 focus:outline-none cursor-pointer"
                      >
                        {services.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.name} {s.doc_count !== undefined ? `(${s.doc_count})` : ''}
                          </option>
                        ))}
                        <option value="__add_new__">+ Add Microservice...</option>
                      </select>
                      <ChevronDown className="w-3 h-3 text-slate-400 absolute right-2 top-2 pointer-events-none" />
                    </div>
                  </div>

                  {models.length > 0 && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-bold text-slate-400 tracking-wider uppercase flex items-center gap-1">
                        <Cpu className="w-3 h-3 text-[#f05a28]" />
                        MODEL
                      </span>
                      <div className="relative">
                        <select
                          value={selectedModel}
                          onChange={(e) => setSelectedModel(e.target.value)}
                          className="appearance-none bg-slate-100 hover:bg-slate-200/70 text-slate-700 text-xs font-semibold pl-2.5 pr-6 py-1 rounded-lg border border-slate-200/60 focus:outline-none cursor-pointer"
                        >
                          {models.map((m) => (
                            <option key={m.id} value={m.id}>
                              {m.name} ({m.provider ? m.provider.toUpperCase() : 'LLM'}) {m.is_default ? '(Default)' : ''}
                            </option>
                          ))}
                        </select>
                        <ChevronDown className="w-3 h-3 text-slate-400 absolute right-2 top-2 pointer-events-none" />
                      </div>
                    </div>
                  )}
                </div>

                {/* Middle Row: Text Input */}
                <textarea
                  value={queryInput}
                  onChange={(e) => setQueryInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleStartChat();
                    }
                  }}
                  placeholder={`Ask a follow up question about ${selectedService}...`}
                  rows={2}
                  disabled={isLoading}
                  className="w-full resize-none bg-transparent text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none py-1"
                />

                {/* Bottom Row: Circular Orange Up-Arrow Send Button */}
                <div className="flex items-center justify-between pt-1">
                  <span className="text-[10px] text-slate-400">
                    Press Enter to send, Shift + Enter for new line
                  </span>
                  <button
                    onClick={() => handleStartChat()}
                    disabled={!queryInput.trim() || isLoading}
                    type="button"
                    className={`w-7 h-7 rounded-full flex items-center justify-center transition-all cursor-pointer ${
                      queryInput.trim() && !isLoading
                        ? 'bg-[#f05a28] text-white shadow-xs hover:bg-[#d94b1c]'
                        : 'bg-orange-100 text-[#f05a28] hover:bg-[#f05a28] hover:text-white'
                    }`}
                    title="Send message"
                  >
                    {isLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <ArrowUp className="w-4 h-4 stroke-[2.5]" />
                    )}
                  </button>
                </div>
              </div>
            </div>

          </main>
        )}

      </div>

      {/* Knowledge Ingestion Modal */}
      <IngestionModal
        isOpen={isIngestionModalOpen}
        onClose={() => setIsIngestionModalOpen(false)}
        service={selectedService}
        services={services}
        onServiceCreated={(newService) => {
          setServices((prev) => [...prev, newService]);
          setSelectedService(newService.id);
        }}
        onSuccess={async () => {
          const updated = await apiClient.listServices();
          if (updated && updated.length > 0) setServices(updated);
        }}
      />

      {/* Conversation History Drawer */}
      <ConversationHistoryDrawer
        isOpen={isHistoryDrawerOpen}
        onClose={() => setIsHistoryDrawerOpen(false)}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleResetHome}
      />

      {/* Share Conversation Modal */}
      <ShareModal
        isOpen={isShareModalOpen}
        onClose={() => setIsShareModalOpen(false)}
        conversationId={currentConversationId}
        shareToken={shareToken}
        isLoading={isSharingLoading}
      />

      {/* Course Context Document Viewer Modal */}
      {activeSourceModal.isOpen && (
        <DocumentViewerModal
          isOpen={activeSourceModal.isOpen}
          onClose={() =>
            setActiveSourceModal({
              isOpen: false,
              file: '',
              service: 'income-assessment-service',
            })
          }
          file={activeSourceModal.file}
          service={activeSourceModal.service}
        />
      )}
    </div>
  );
}

export function App() {
  return (
    <AuthProvider>
      <DashboardApp />
    </AuthProvider>
  );
}

export default App;

