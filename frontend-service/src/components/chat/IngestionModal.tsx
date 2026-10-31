import React, { useState, useEffect, useRef } from 'react';
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  Clock,
  Eye,
  FileCode,
  FileText,
  FolderArchive,
  Loader2,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
  UploadCloud,
  X,
} from 'lucide-react';
import apiClient from '@/lib/api/client';
import type {
  CourseIngestResponse,
  CourseUploadResponse,
  DocumentDetailResponse,
  KnowledgeFileInfo,
  KnowledgeIngestResponse,
  KnowledgeUploadResponse,
  Microservice,
  PendingCourseInfo,
} from '@/types';
import { MarkdownRenderer } from './MarkdownRenderer';

interface IngestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  service: string;
  services?: Microservice[];
  onSuccess?: (result: KnowledgeIngestResponse) => void;
  onServiceCreated?: (newService: Microservice) => void;
}

export function IngestionModal({
  isOpen,
  onClose,
  service: initialService,
  services: initialServices,
  onSuccess,
  onServiceCreated,
}: IngestionModalProps) {
  const [activeTab, setActiveTab] = useState<'dev-chat' | 'knowledge-cafe'>('dev-chat');
  const [currentService, setCurrentService] = useState<string>(initialService);
  const [localServices, setLocalServices] = useState<Microservice[]>(initialServices || []);
  const [isCreatingService, setIsCreatingService] = useState(false);
  const [newServiceId, setNewServiceId] = useState('');
  const [newServiceName, setNewServiceName] = useState('');
  const [isSubmittingService, setIsSubmittingService] = useState(false);

  // Dev Chat (Docs) state
  const [docInputMode, setDocInputMode] = useState<'upload' | 'write-md'>('upload');
  const [customMdName, setCustomMdName] = useState<string>('');
  const [customMdContent, setCustomMdContent] = useState<string>('');
  const [isSavingCustomMd, setIsSavingCustomMd] = useState<boolean>(false);
  const [docFiles, setDocFiles] = useState<KnowledgeFileInfo[]>([]);
  const [isFilesLoading, setIsFilesLoading] = useState(false);
  const [selectedDocFile, setSelectedDocFile] = useState<File | null>(null);
  const [isUploadingDoc, setIsUploadingDoc] = useState(false);
  const [isIngestingDocs, setIsIngestingDocs] = useState(false);
  const [isReindexing, setIsReindexing] = useState(false);
  const [docUploadSuccess, setDocUploadSuccess] = useState<string | null>(null);
  const [docIngestResult, setDocIngestResult] = useState<KnowledgeIngestResponse | null>(null);
  const [docError, setDocError] = useState<string | null>(null);
  const [isDraggingDoc, setIsDraggingDoc] = useState(false);

  // Document preview state
  const [previewDoc, setPreviewDoc] = useState<DocumentDetailResponse | null>(null);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);

  // Knowledge Cafe (Course ZIP) state
  const [pendingCourses, setPendingCourses] = useState<PendingCourseInfo[]>([]);
  const [isCoursesLoading, setIsCoursesLoading] = useState(false);
  const [selectedZipFile, setSelectedZipFile] = useState<File | null>(null);
  const [isUploadingZip, setIsUploadingZip] = useState(false);
  const [ingestingCourseId, setIngestingCourseId] = useState<string | null>(null);
  const [courseUploadSuccess, setCourseUploadSuccess] = useState<string | null>(null);
  const [courseIngestSuccess, setCourseIngestSuccess] = useState<CourseIngestResponse | null>(null);
  const [courseError, setCourseError] = useState<string | null>(null);
  const [isDraggingZip, setIsDraggingZip] = useState(false);

  const docFileInputRef = useRef<HTMLInputElement>(null);
  const zipFileInputRef = useRef<HTMLInputElement>(null);

  // Sync service and services props
  useEffect(() => {
    if (initialServices) {
      setLocalServices(initialServices);
      if (initialServices.length === 0) {
        setIsCreatingService(true);
      }
    }
  }, [initialServices]);

  useEffect(() => {
    if (initialService) {
      setCurrentService(initialService);
    } else if (localServices.length > 0 && !currentService) {
      setCurrentService(localServices[0].id);
    }
  }, [initialService, localServices]);

  // Load microservice files
  const loadFiles = async (svc: string) => {
    if (!svc) {
      setDocFiles([]);
      return;
    }
    setIsFilesLoading(true);
    try {
      const data = await apiClient.listKnowledgeFiles(svc);
      setDocFiles(data);
    } catch (err: any) {
      console.error('Failed to load files:', err);
    } finally {
      setIsFilesLoading(false);
    }
  };

  // Load pending courses
  const loadPendingCourses = async () => {
    setIsCoursesLoading(true);
    try {
      const data = await apiClient.listPendingCourses();
      setPendingCourses(data);
    } catch (err: any) {
      console.error('Failed to load pending courses:', err);
    } finally {
      setIsCoursesLoading(false);
    }
  };

  // Refresh data on open or tab change
  useEffect(() => {
    if (isOpen) {
      if (activeTab === 'dev-chat') {
        loadFiles(currentService);
      } else {
        loadPendingCourses();
      }
    }
  }, [isOpen, activeTab, currentService]);

  if (!isOpen) return null;

  // Format file size
  const formatBytes = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // -------------------------------------------------------------
  // Dev Chat Handlers
  // -------------------------------------------------------------
  const handleDocFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const f = e.target.files[0];
      const ext = f.name.toLowerCase();
      const isAllowed =
        ext.endsWith('.md') ||
        ext.endsWith('.markdown') ||
        ext.endsWith('.pdf') ||
        ext.endsWith('.kt') ||
        ext.endsWith('.kts') ||
        ext.endsWith('.java') ||
        ext.endsWith('.py') ||
        ext.endsWith('.zip');
      if (!isAllowed) {
        setDocError('Supported formats: Kotlin (.kt, .kts), Java (.java), Python (.py), Markdown (.md), PDF (.pdf), or .zip archive.');
        return;
      }
      setSelectedDocFile(f);
      setDocError(null);
      setDocUploadSuccess(null);
    }
  };

  const handleSaveCustomMd = async (e: React.FormEvent) => {
    e.preventDefault();
    const rawName = customMdName.trim();
    const body = customMdContent.trim();
    if (!rawName || !body) {
      setDocError('Please provide both a file name and Markdown content.');
      return;
    }
    const safeName = rawName.toLowerCase().endsWith('.md') || rawName.toLowerCase().endsWith('.markdown')
      ? rawName
      : `${rawName}.md`;

    setIsSavingCustomMd(true);
    setDocError(null);
    setDocUploadSuccess(null);
    try {
      const mdFile = new File([body], safeName, { type: 'text/markdown' });
      const res: KnowledgeUploadResponse = await apiClient.uploadKnowledgeFile(currentService, mdFile);
      setDocUploadSuccess(res.message);
      setCustomMdName('');
      setCustomMdContent('');
      await loadFiles(currentService);
    } catch (err: any) {
      setDocError(err.message || 'Failed to save custom Markdown context file');
    } finally {
      setIsSavingCustomMd(false);
    }
  };

  const handleUploadDoc = async () => {
    if (!selectedDocFile) return;
    setIsUploadingDoc(true);
    setDocError(null);
    setDocUploadSuccess(null);

    try {
      const res: KnowledgeUploadResponse = await apiClient.uploadKnowledgeFile(currentService, selectedDocFile);
      setDocUploadSuccess(res.message);
      setSelectedDocFile(null);
      if (docFileInputRef.current) docFileInputRef.current.value = '';
      await loadFiles(currentService);
    } catch (err: any) {
      setDocError(err.message || 'Failed to upload document');
    } finally {
      setIsUploadingDoc(false);
    }
  };

  const handleCreateService = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newServiceId.trim()) return;
    setIsSubmittingService(true);
    setDocError(null);
    try {
      const created = await apiClient.createService({
        id: newServiceId.trim(),
        name: newServiceName.trim() || undefined,
      });
      setLocalServices((prev) => {
        if (prev.some((s) => s.id === created.id)) return prev;
        return [...prev, created];
      });
      setCurrentService(created.id);
      setIsCreatingService(false);
      setNewServiceId('');
      setNewServiceName('');
      if (onServiceCreated) onServiceCreated(created);
      await loadFiles(created.id);
    } catch (err: any) {
      setDocError(err.message || 'Failed to register microservice');
    } finally {
      setIsSubmittingService(false);
    }
  };

  const handleTriggerReindex = async () => {
    if (!window.confirm(`Are you sure you want to clear and re-index all vectors for '${currentService}'?`)) {
      return;
    }
    setIsReindexing(true);
    setDocError(null);
    setDocIngestResult(null);

    try {
      const res = await apiClient.reindexKnowledge(currentService);
      setDocIngestResult(res);
      if (onSuccess) onSuccess(res);
      await loadFiles(currentService);
    } catch (err: any) {
      setDocError(err.message || 'Failed to clear and re-index');
    } finally {
      setIsReindexing(false);
    }
  };

  const handleTriggerDocIngestion = async () => {
    setIsIngestingDocs(true);
    setDocError(null);
    setDocIngestResult(null);

    try {
      const res = await apiClient.triggerKnowledgeIngestion(currentService);
      setDocIngestResult(res);
      if (onSuccess) onSuccess(res);
      await loadFiles(currentService);
    } catch (err: any) {
      setDocError(err.message || 'Failed to trigger ingestion');
    } finally {
      setIsIngestingDocs(false);
    }
  };


  const handlePreviewDoc = async (filename: string) => {
    setIsPreviewLoading(true);
    try {
      const doc = await apiClient.getDocument(currentService, filename);
      setPreviewDoc(doc);
    } catch (err: any) {
      setDocError(`Failed to load document preview: ${err.message}`);
    } finally {
      setIsPreviewLoading(false);
    }
  };

  // -------------------------------------------------------------
  // Knowledge Cafe Handlers
  // -------------------------------------------------------------
  const handleZipFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const f = e.target.files[0];
      if (!f.name.toLowerCase().endsWith('.zip')) {
        setCourseError('Only .zip archives containing course-structure.md are supported.');
        return;
      }
      setSelectedZipFile(f);
      setCourseError(null);
      setCourseUploadSuccess(null);
    }
  };

  const handleUploadZip = async () => {
    if (!selectedZipFile) return;
    setIsUploadingZip(true);
    setCourseError(null);
    setCourseUploadSuccess(null);

    try {
      const res: CourseUploadResponse = await apiClient.uploadCourseZip(selectedZipFile);
      setCourseUploadSuccess(res.message);
      setSelectedZipFile(null);
      if (zipFileInputRef.current) zipFileInputRef.current.value = '';
      await loadPendingCourses();
    } catch (err: any) {
      setCourseError(err.message || 'Failed to upload course zip package');
    } finally {
      setIsUploadingZip(false);
    }
  };

  const handleTriggerCourseIngestion = async (courseId: string) => {
    setIngestingCourseId(courseId);
    setCourseError(null);
    setCourseIngestSuccess(null);

    try {
      const res = await apiClient.triggerCourseIngestion(courseId);
      setCourseIngestSuccess(res);
      await loadPendingCourses();
    } catch (err: any) {
      setCourseError(err.message || `Failed to index course ${courseId}`);
    } finally {
      setIngestingCourseId(null);
    }
  };

  const pendingDocsCount = docFiles.filter((f) => f.status === 'pending').length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="bg-white rounded-3xl border border-slate-200 shadow-2xl max-w-2xl w-full my-8 p-6 space-y-5 animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-orange-100 text-[#f05a28] flex items-center justify-center shadow-2xs">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-slate-900">Knowledge Ingestion & Staging</h3>
              <p className="text-xs text-slate-500">Upload documentation & courses for verification before indexing</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Switcher: Dev Chat vs Knowledge Cafe */}
        <div className="flex bg-slate-100 p-1 rounded-2xl">
          <button
            onClick={() => setActiveTab('dev-chat')}
            className={`flex-1 py-2 text-xs font-bold rounded-xl flex items-center justify-center gap-2 transition-all cursor-pointer ${
              activeTab === 'dev-chat'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <FileText className="w-4 h-4 text-[#f05a28]" />
            <span>Code & Docs (.kt, .java, .py, .md, .pdf)</span>
            {pendingDocsCount > 0 && (
              <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-amber-500 text-white font-bold">
                {pendingDocsCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('knowledge-cafe')}
            className={`flex-1 py-2 text-xs font-bold rounded-xl flex items-center justify-center gap-2 transition-all cursor-pointer ${
              activeTab === 'knowledge-cafe'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <BookOpen className="w-4 h-4 text-[#f05a28]" />
            <span>Knowledge Cafe Courses (.zip)</span>
            {pendingCourses.length > 0 && (
              <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-amber-500 text-white font-bold">
                {pendingCourses.length}
              </span>
            )}
          </button>
        </div>

        {/* ========================================================================= */}
        {/* TAB 1: DEV CHAT MICROSERVICE DOCS */}
        {/* ========================================================================= */}
        {activeTab === 'dev-chat' && (
          <div className="space-y-4">
            {/* Service Selector & Inline Creation */}
            <div className="bg-slate-50 border border-slate-200/80 px-4 py-2.5 rounded-2xl">
              {!isCreatingService ? (
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-700">Target Microservice:</span>
                    <select
                      value={currentService}
                      onChange={(e) => {
                        setCurrentService(e.target.value);
                        loadFiles(e.target.value);
                      }}
                      className="text-xs font-mono font-semibold bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-slate-800 focus:outline-none focus:ring-1 focus:ring-orange-400 cursor-pointer"
                    >
                      {localServices.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name} ({s.id})
                        </option>
                      ))}
                    </select>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsCreatingService(true)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-[#f05a28] hover:bg-orange-50 border border-orange-200 rounded-lg transition-colors cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>New Microservice</span>
                  </button>
                </div>
              ) : (
                <form onSubmit={handleCreateService} className="flex flex-col sm:flex-row items-center gap-2">
                  <input
                    type="text"
                    required
                    placeholder="service-id (e.g. payment-service)"
                    value={newServiceId}
                    onChange={(e) => setNewServiceId(e.target.value)}
                    className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-800 font-mono placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-orange-400"
                  />
                  <input
                    type="text"
                    placeholder="Display Name (optional)"
                    value={newServiceName}
                    onChange={(e) => setNewServiceName(e.target.value)}
                    className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-orange-400"
                  />
                  <div className="flex items-center gap-1.5">
                    <button
                      type="submit"
                      disabled={isSubmittingService || !newServiceId.trim()}
                      className="px-3 py-1.5 bg-[#f05a28] hover:bg-[#d94b1c] text-white text-xs font-bold rounded-lg transition-colors disabled:opacity-50 cursor-pointer"
                    >
                      {isSubmittingService ? 'Registering...' : 'Add Service'}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setIsCreatingService(false);
                        setNewServiceId('');
                        setNewServiceName('');
                      }}
                      className="px-2.5 py-1.5 text-xs text-slate-500 hover:text-slate-700 rounded-lg transition-colors cursor-pointer"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              )}
            </div>

            {/* Mode Toggle: Upload Files vs Write Custom .md Context */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setDocInputMode('upload')}
                className={`flex-1 py-1.5 px-3 rounded-xl text-xs font-semibold border transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
                  docInputMode === 'upload'
                    ? 'bg-orange-50/80 border-[#f05a28] text-[#f05a28]'
                    : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                <UploadCloud className="w-3.5 h-3.5" />
                <span>Upload Source & Docs</span>
              </button>
              <button
                type="button"
                onClick={() => setDocInputMode('write-md')}
                className={`flex-1 py-1.5 px-3 rounded-xl text-xs font-semibold border transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
                  docInputMode === 'write-md'
                    ? 'bg-orange-50/80 border-[#f05a28] text-[#f05a28]'
                    : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Write Custom .md Context</span>
              </button>
            </div>

            {docInputMode === 'upload' ? (
              /* Drag & Drop Upload Zone */
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDraggingDoc(true);
                }}
                onDragLeave={() => setIsDraggingDoc(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDraggingDoc(false);
                  if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    const f = e.dataTransfer.files[0];
                    const ext = f.name.toLowerCase();
                    const isAllowed =
                      ext.endsWith('.md') ||
                      ext.endsWith('.markdown') ||
                      ext.endsWith('.pdf') ||
                      ext.endsWith('.kt') ||
                      ext.endsWith('.kts') ||
                      ext.endsWith('.java') ||
                      ext.endsWith('.py') ||
                      ext.endsWith('.zip');
                    if (!isAllowed) {
                      setDocError('Supported formats: Kotlin (.kt, .kts), Java (.java), Python (.py), Markdown (.md), PDF (.pdf), or .zip archive.');
                      return;
                    }
                    setSelectedDocFile(f);
                    setDocError(null);
                    setDocUploadSuccess(null);
                  }
                }}
                className={`border-2 border-dashed rounded-2xl p-5 text-center transition-all ${
                  isDraggingDoc
                    ? 'border-[#f05a28] bg-orange-50/50'
                    : 'border-slate-200 hover:border-slate-300 bg-slate-50/50'
                }`}
              >
                <input
                  ref={docFileInputRef}
                  type="file"
                  accept=".md,.markdown,.pdf,.kt,.kts,.java,.py,.zip"
                  onChange={handleDocFileSelect}
                  className="hidden"
                  id="doc-file-input"
                />
                <div className="flex flex-col items-center gap-2">
                  <div className="w-10 h-10 rounded-full bg-orange-100 text-[#f05a28] flex items-center justify-center">
                    <UploadCloud className="w-5 h-5" />
                  </div>
                  <div>
                    <label
                      htmlFor="doc-file-input"
                      className="text-xs font-bold text-[#f05a28] hover:underline cursor-pointer"
                    >
                      Click to browse
                    </label>
                    <span className="text-xs text-slate-500"> or drag and drop your file or zip folder</span>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Supported formats: <strong className="text-slate-600">Kotlin (.kt, .kts)</strong>, <strong className="text-slate-600">Java (.java)</strong>, <strong className="text-slate-600">Python (.py)</strong>, <strong className="text-slate-600">Markdown (.md)</strong>, <strong className="text-slate-600">PDF (.pdf)</strong>, or <strong className="text-slate-600">ZIP (.zip)</strong>
                  </p>
                </div>

                {selectedDocFile && (
                  <div className="mt-3 inline-flex items-center gap-3 px-3 py-1.5 bg-white border border-slate-200 rounded-xl shadow-2xs">
                    <div className="flex items-center gap-1.5 text-xs font-medium text-slate-800">
                      {selectedDocFile.name.toLowerCase().endsWith('.zip') ? (
                        <FolderArchive className="w-3.5 h-3.5 text-[#f05a28]" />
                      ) : selectedDocFile.name.toLowerCase().endsWith('.kt') ||
                        selectedDocFile.name.toLowerCase().endsWith('.kts') ||
                        selectedDocFile.name.toLowerCase().endsWith('.java') ||
                        selectedDocFile.name.toLowerCase().endsWith('.py') ? (
                        <FileCode className="w-3.5 h-3.5 text-purple-600" />
                      ) : (
                        <FileText className="w-3.5 h-3.5 text-[#f05a28]" />
                      )}
                      <span className="truncate max-w-[200px]">{selectedDocFile.name}</span>
                      <span className="text-slate-400 text-[10px]">({formatBytes(selectedDocFile.size)})</span>
                    </div>
                    <button
                      onClick={handleUploadDoc}
                      disabled={isUploadingDoc}
                      className="flex items-center gap-1 px-3 py-1 bg-[#f05a28] hover:bg-[#d94b1c] text-white text-[11px] font-bold rounded-lg shadow-2xs transition-colors cursor-pointer disabled:opacity-50"
                    >
                      {isUploadingDoc ? (
                        <>
                          <Loader2 className="w-3 h-3 animate-spin" />
                          <span>Uploading...</span>
                        </>
                      ) : (
                        <>
                          <UploadCloud className="w-3 h-3" />
                          <span>
                            {selectedDocFile.name.toLowerCase().endsWith('.zip')
                              ? 'Unpack & Stage ZIP'
                              : 'Upload to Staging'}
                          </span>
                        </>
                      )}
                    </button>
                  </div>
                )}
              </div>
            ) : (
              /* Author & Save Custom .md Context Note */
              <form
                onSubmit={handleSaveCustomMd}
                className="border border-slate-200 rounded-2xl p-4 bg-slate-50/60 space-y-3"
              >
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                  <label className="text-xs font-bold text-slate-700">
                    Author Custom Markdown Context (.md)
                  </label>
                  <span className="text-[10px] text-slate-400">
                    Tip: Wrap class/function names in backticks (e.g. <code className="font-mono">`OrderService`</code>) to link them in 1-hop retrieval
                  </span>
                </div>
                <input
                  type="text"
                  required
                  placeholder="File name (e.g. architecture-overview.md or domain-rules.md)"
                  value={customMdName}
                  onChange={(e) => setCustomMdName(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-mono text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-orange-400"
                />
                <textarea
                  rows={5}
                  required
                  placeholder="# Service Architecture & Domain Notes&#10;&#10;Document key flows, business rules, or component responsibilities for this microservice..."
                  value={customMdContent}
                  onChange={(e) => setCustomMdContent(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-xl p-3 text-xs font-mono text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-orange-400"
                />
                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={isSavingCustomMd || !customMdName.trim() || !customMdContent.trim()}
                    className="flex items-center gap-1.5 px-4 py-1.5 bg-[#f05a28] hover:bg-[#d94b1c] text-white text-xs font-bold rounded-xl shadow-2xs transition-colors cursor-pointer disabled:opacity-50"
                  >
                    {isSavingCustomMd ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Saving .md Context...</span>
                      </>
                    ) : (
                      <>
                        <FileText className="w-3.5 h-3.5" />
                        <span>Save .md to Staged Context</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}

            {/* Alerts */}
            {docUploadSuccess && (
              <div className="flex items-start gap-2.5 p-3 bg-amber-50 border border-amber-200 rounded-2xl text-xs text-amber-800">
                <Clock className="w-4 h-4 shrink-0 text-amber-600 mt-0.5" />
                <div>
                  <span className="font-bold block">Document Staged Under Pending Review</span>
                  <span>{docUploadSuccess}</span>
                </div>
              </div>
            )}

            {docError && (
              <div className="flex items-start gap-2.5 p-3 bg-rose-50 border border-rose-200 rounded-2xl text-xs text-rose-800">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 mt-0.5" />
                <div>{docError}</div>
              </div>
            )}

            {/* Document List Table */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-700">Documents in Service ({docFiles.length})</span>
                <span className="text-[11px] text-slate-400 font-mono">
                  Pending: {docFiles.filter((f) => f.status === 'pending').length} | Ingested: {docFiles.filter((f) => f.status === 'ingested').length}
                </span>
              </div>

              <div className="border border-slate-200 rounded-2xl overflow-hidden max-h-48 overflow-y-auto">
                {isFilesLoading ? (
                  <div className="p-6 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin text-[#f05a28]" />
                    <span>Loading documents...</span>
                  </div>
                ) : docFiles.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-400">
                    No documents found for microservice <code className="font-mono">{currentService}</code>.
                  </div>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {docFiles.map((file) => (
                      <div
                        key={file.path}
                        className={`flex items-center justify-between px-3.5 py-2.5 text-xs transition-colors ${
                          file.status === 'pending' ? 'bg-amber-50/40 hover:bg-amber-50/70' : 'hover:bg-slate-50'
                        }`}
                      >
                        <div className="flex items-center gap-2.5 truncate pr-2">
                          <span
                            className={`px-1.5 py-0.5 rounded-md text-[9px] font-mono font-bold ${
                              file.format === 'PDF'
                                ? 'bg-rose-100 text-rose-700'
                                : file.format === 'KT' || file.format === 'KOTLIN'
                                ? 'bg-purple-100 text-purple-700'
                                : file.format === 'JAVA'
                                ? 'bg-amber-100 text-amber-800'
                                : file.format === 'PY' || file.format === 'PYTHON'
                                ? 'bg-emerald-100 text-emerald-800'
                                : 'bg-blue-100 text-blue-700'
                            }`}
                          >
                            {file.format}
                          </span>
                          <span className="font-medium text-slate-800 truncate" title={file.name}>
                            {file.name}
                          </span>
                          <span className="text-[10px] text-slate-400 shrink-0">
                            {formatBytes(file.size_bytes)}
                          </span>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          {file.status === 'pending' ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-700 border border-amber-200">
                              <Clock className="w-3 h-3 text-amber-600" />
                              Pending Review
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700 border border-emerald-200">
                              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                              Ingested
                            </span>
                          )}

                          <button
                            onClick={() => handlePreviewDoc(file.name)}
                            disabled={isPreviewLoading}
                            className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors cursor-pointer disabled:opacity-50"
                            title="Preview document content"
                          >
                            {isPreviewLoading ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin text-[#f05a28]" />
                            ) : (
                              <Eye className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Ingestion Results Feedback */}
            {docIngestResult && (
              <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-2xl space-y-2">
                <div className="flex items-center gap-2 text-emerald-800 font-bold text-xs">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Ingestion Completed Successfully!</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div className="bg-white p-2 rounded-xl border border-emerald-100">
                    <span className="text-[10px] text-slate-400 block uppercase">Files Processed</span>
                    <span className="text-sm font-bold text-slate-800">{docIngestResult.total_files}</span>
                  </div>
                  <div className="bg-white p-2 rounded-xl border border-emerald-100">
                    <span className="text-[10px] text-slate-400 block uppercase">Chunks Indexed (768d + BM25)</span>
                    <span className="text-sm font-bold text-[#f05a28]">{docIngestResult.total_chunks}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Maintainer Actions Footer */}
            <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="text-[11px] text-slate-400 max-w-[300px]">
                <strong className="text-slate-600">Hybrid Retrieval & RepoMap:</strong> Jina-Code-v2 (768-dim, 8K) + Sparse BM25 RRF & 1-hop graph.
              </div>
              <div className="flex items-center gap-2 self-end sm:self-auto">
                <button
                  type="button"
                  onClick={handleTriggerReindex}
                  disabled={isIngestingDocs || isReindexing}
                  className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-50 border border-rose-200 rounded-full transition-colors cursor-pointer disabled:opacity-50"
                  title="Wipe previous Qdrant vectors for this microservice and re-index from scratch"
                >
                  {isReindexing ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Re-indexing...</span>
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Clear & Re-index</span>
                    </>
                  )}
                </button>
                <button
                  onClick={handleTriggerDocIngestion}
                  disabled={isIngestingDocs || isReindexing}
                  className="flex items-center gap-1.5 px-5 py-2.5 text-xs font-bold bg-[#f05a28] hover:bg-[#d94b1c] text-white rounded-full shadow-xs transition-all cursor-pointer disabled:opacity-50"
                >
                  {isIngestingDocs ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Indexing Vector Store...</span>
                    </>
                  ) : (
                    <>
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>Trigger Ingestion</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 2: KNOWLEDGE CAFE COURSES (.ZIP) */}
        {/* ========================================================================= */}
        {activeTab === 'knowledge-cafe' && (
          <div className="space-y-4">
            <div className="p-3 bg-blue-50/60 border border-blue-200/80 rounded-2xl flex items-start gap-3">
              <FolderArchive className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
              <div className="text-xs text-blue-900 leading-relaxed">
                <span className="font-bold block mb-0.5">Course Package Structure</span>
                Upload a <strong className="font-mono">.zip</strong> containing{' '}
                <strong className="font-mono">course-structure.md</strong> and lesson context files. Uploading stages the course for manual verification without indexing into Qdrant.
              </div>
            </div>

            {/* Drag & Drop Zip Zone */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDraggingZip(true);
              }}
              onDragLeave={() => setIsDraggingZip(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDraggingZip(false);
                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                  const f = e.dataTransfer.files[0];
                  if (!f.name.toLowerCase().endsWith('.zip')) {
                    setCourseError('Only .zip archives containing course-structure.md are supported.');
                    return;
                  }
                  setSelectedZipFile(f);
                  setCourseError(null);
                  setCourseUploadSuccess(null);
                }
              }}
              className={`border-2 border-dashed rounded-2xl p-5 text-center transition-all ${
                isDraggingZip
                  ? 'border-[#f05a28] bg-orange-50/50'
                  : 'border-slate-200 hover:border-slate-300 bg-slate-50/50'
              }`}
            >
              <input
                ref={zipFileInputRef}
                type="file"
                accept=".zip"
                onChange={handleZipFileSelect}
                className="hidden"
                id="zip-file-input"
              />
              <div className="flex flex-col items-center gap-2">
                <div className="w-10 h-10 rounded-full bg-orange-100 text-[#f05a28] flex items-center justify-center">
                  <FolderArchive className="w-5 h-5" />
                </div>
                <div>
                  <label
                    htmlFor="zip-file-input"
                    className="text-xs font-bold text-[#f05a28] hover:underline cursor-pointer"
                  >
                    Click to browse course zip
                  </label>
                  <span className="text-xs text-slate-500"> or drag and drop archive</span>
                </div>
                <p className="text-[11px] text-slate-400">
                  Accepted package: <strong className="text-slate-600">Compressed ZIP folder (.zip)</strong>
                </p>
              </div>

              {selectedZipFile && (
                <div className="mt-3 inline-flex items-center gap-3 px-3 py-1.5 bg-white border border-slate-200 rounded-xl shadow-2xs">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-slate-800">
                    <FolderArchive className="w-3.5 h-3.5 text-[#f05a28]" />
                    <span className="truncate max-w-[200px]">{selectedZipFile.name}</span>
                    <span className="text-slate-400 text-[10px]">({formatBytes(selectedZipFile.size)})</span>
                  </div>
                  <button
                    onClick={handleUploadZip}
                    disabled={isUploadingZip}
                    className="flex items-center gap-1 px-3 py-1 bg-[#f05a28] hover:bg-[#d94b1c] text-white text-[11px] font-bold rounded-lg shadow-2xs transition-colors cursor-pointer disabled:opacity-50"
                  >
                    {isUploadingZip ? (
                      <>
                        <Loader2 className="w-3 h-3 animate-spin" />
                        <span>Extracting & Validating...</span>
                      </>
                    ) : (
                      <>
                        <UploadCloud className="w-3 h-3" />
                        <span>Upload Course ZIP</span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>

            {/* Feedback Alerts */}
            {courseUploadSuccess && (
              <div className="flex items-start gap-2.5 p-3 bg-amber-50 border border-amber-200 rounded-2xl text-xs text-amber-800">
                <Clock className="w-4 h-4 shrink-0 text-amber-600 mt-0.5" />
                <div>
                  <span className="font-bold block">Course Package Staged Under Pending Review</span>
                  <span>{courseUploadSuccess}</span>
                </div>
              </div>
            )}

            {courseIngestSuccess && (
              <div className="flex items-start gap-2.5 p-3 bg-emerald-50 border border-emerald-200 rounded-2xl text-xs text-emerald-800">
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600 mt-0.5" />
                <div>
                  <span className="font-bold block">Course Published & Indexed!</span>
                  <span>{courseIngestSuccess.message}</span>
                </div>
              </div>
            )}

            {courseError && (
              <div className="flex items-start gap-2.5 p-3 bg-rose-50 border border-rose-200 rounded-2xl text-xs text-rose-800">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 mt-0.5" />
                <div>{courseError}</div>
              </div>
            )}

            {/* Pending Courses List */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-700">Pending Courses Staged for Ingestion ({pendingCourses.length})</span>
                <button
                  onClick={loadPendingCourses}
                  className="text-[11px] text-[#f05a28] hover:underline cursor-pointer flex items-center gap-1"
                >
                  <RefreshCw className="w-3 h-3" />
                  Refresh
                </button>
              </div>

              <div className="border border-slate-200 rounded-2xl overflow-hidden max-h-52 overflow-y-auto">
                {isCoursesLoading ? (
                  <div className="p-6 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin text-[#f05a28]" />
                    <span>Loading staged courses...</span>
                  </div>
                ) : pendingCourses.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-400">
                    No courses currently pending verification. Upload a zipped course above to stage one.
                  </div>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {pendingCourses.map((course) => (
                      <div
                        key={course.course_id}
                        className="p-3.5 bg-amber-50/30 hover:bg-amber-50/60 transition-colors flex items-center justify-between gap-3"
                      >
                        <div className="space-y-1 truncate">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-xs text-slate-900 truncate">
                              {course.title}
                            </span>
                            <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-amber-100 text-amber-700 border border-amber-200">
                              Pending Review
                            </span>
                          </div>
                          <div className="flex items-center gap-3 text-[11px] text-slate-500 font-mono">
                            <span>ID: {course.course_id}</span>
                            <span>•</span>
                            <span>Service: {course.target_service}</span>
                            <span>•</span>
                            <span>{course.total_lessons} lessons</span>
                          </div>
                        </div>

                        <button
                          onClick={() => handleTriggerCourseIngestion(course.course_id)}
                          disabled={ingestingCourseId === course.course_id}
                          className="flex items-center gap-1.5 px-4 py-2 bg-[#f05a28] hover:bg-[#d94b1c] text-white text-xs font-bold rounded-xl shadow-xs transition-all cursor-pointer shrink-0 disabled:opacity-50"
                        >
                          {ingestingCourseId === course.course_id ? (
                            <>
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              <span>Indexing Course...</span>
                            </>
                          ) : (
                            <>
                              <Sparkles className="w-3.5 h-3.5" />
                              <span>Publish & Ingest</span>
                            </>
                          )}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Footer Close */}
        <div className="flex items-center justify-end pt-2 border-t border-slate-100">
          <button
            onClick={onClose}
            className="px-5 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-full transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>

      </div>

      {/* Embedded Document Preview Drawer/Modal */}
      {previewDoc && (
        <div className="fixed inset-0 z-60 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-3xl border border-slate-200 shadow-2xl max-w-2xl w-full max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 bg-slate-50/50">
              <div className="flex items-center gap-2">
                <FileCode className="w-4 h-4 text-[#f05a28]" />
                <span className="font-bold text-sm text-slate-800">{previewDoc.file}</span>
                <span className="text-[10px] text-slate-400 font-mono">({previewDoc.total_lines} lines)</span>
              </div>
              <button
                onClick={() => setPreviewDoc(null)}
                className="p-1.5 rounded-full hover:bg-slate-200 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Content Body */}
            <div className="flex-1 p-5 overflow-y-auto font-sans text-xs leading-relaxed">
              {previewDoc.file.toLowerCase().endsWith('.kt') || previewDoc.file.toLowerCase().endsWith('.kts') ? (
                <MarkdownRenderer content={`\`\`\`kotlin\n${previewDoc.content}\n\`\`\``} />
              ) : previewDoc.file.toLowerCase().endsWith('.java') ? (
                <MarkdownRenderer content={`\`\`\`java\n${previewDoc.content}\n\`\`\``} />
              ) : previewDoc.file.toLowerCase().endsWith('.py') ? (
                <MarkdownRenderer content={`\`\`\`python\n${previewDoc.content}\n\`\`\``} />
              ) : (
                <MarkdownRenderer content={previewDoc.content} />
              )}
            </div>

            {/* Footer */}
            <div className="px-5 py-3 border-t border-slate-100 bg-slate-50/50 flex justify-end">
              <button
                onClick={() => setPreviewDoc(null)}
                className="px-4 py-1.5 text-xs font-semibold bg-slate-200 hover:bg-slate-300 text-slate-800 rounded-full transition-colors cursor-pointer"
              >
                Back to Document List
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
