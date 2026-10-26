import React, { useEffect, useState } from 'react';
import {
  BookOpen,
  Check,
  Code,
  Download,
  Eye,
  Loader2,
  X,
} from 'lucide-react';
import apiClient from '@/lib/api/client';
import type { DocumentDetailResponse } from '@/types';
import { MarkdownRenderer } from './MarkdownRenderer';

interface DocumentViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  service: string;
  file: string;
  startLine?: number;
  endLine?: number;
}

export const DocumentViewerModal: React.FC<DocumentViewerModalProps> = ({
  isOpen,
  onClose,
  service,
  file,
  startLine,
  endLine,
}) => {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [docData, setDocData] = useState<DocumentDetailResponse | null>(null);
  const [viewMode, setViewMode] = useState<'rendered' | 'raw'>('rendered');
  const [downloaded, setDownloaded] = useState<boolean>(false);

  useEffect(() => {
    if (!isOpen || !file) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    const fetchDoc = async () => {
      try {
        let data: DocumentDetailResponse;
        if (
          service.includes('-kt') ||
          service.includes('pipelines') ||
          service.includes('jenkins') ||
          service.includes('course') ||
          service === 'income-assessment-kt'
        ) {
          data = await apiClient.getCourseDocument(service, file);
        } else {
          try {
            data = await apiClient.getDocument(service, file);
          } catch {
            data = await apiClient.getCourseDocument(service, file);
          }
        }
        if (isMounted) {
          setDocData(data);
          setLoading(false);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Failed to load source document.');
          setLoading(false);
        }
      }
    };

    fetchDoc();

    return () => {
      isMounted = false;
    };
  }, [isOpen, service, file]);

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const fileName = file.split('/').pop() || file;
  const lineRangeStr = startLine
    ? endLine && endLine !== startLine
      ? `L${startLine}-${endLine}`
      : `L${startLine}`
    : null;

  const handleDownload = () => {
    if (!docData) return;
    const mimeType = docData.content_type || 'text/markdown;charset=utf-8';
    const blob = new Blob([docData.content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = docData.file || fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setDownloaded(true);
    setTimeout(() => setDownloaded(false), 2000);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    return `${(bytes / 1024).toFixed(1)} KB`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div
        className="relative flex flex-col w-full max-w-5xl h-[90vh] bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-200 bg-slate-50/80 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-xl bg-orange-100 flex items-center justify-center shrink-0 text-[#f05a28] shadow-2xs">
              <BookOpen className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-sm font-bold text-slate-900 font-mono truncate">
                  {fileName}
                </h2>
                <span className="px-2 py-0.5 text-[10px] font-semibold bg-orange-50 text-[#f05a28] border border-orange-200 rounded-md">
                  {service}
                </span>
                {docData && (
                  <span className="text-[11px] text-slate-400">
                    {docData.total_lines} lines • {formatFileSize(docData.size_bytes)}
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-500 truncate mt-0.5">
                Verified Source Documentation
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2 shrink-0">
            {lineRangeStr && (
              <span className="hidden sm:inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-mono font-medium bg-amber-50 text-amber-800 border border-amber-200">
                <span>Cited {lineRangeStr}</span>
              </span>
            )}

            {/* View Mode Toggle */}
            <div className="inline-flex items-center rounded-lg bg-slate-200/80 p-0.5 text-xs font-medium text-slate-600">
              <button
                type="button"
                onClick={() => setViewMode('rendered')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                  viewMode === 'rendered'
                    ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
                title="Rendered Markdown View"
              >
                <Eye className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Preview</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode('raw')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                  viewMode === 'raw'
                    ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
                title="Raw Markdown Source"
              >
                <Code className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Raw</span>
              </button>
            </div>

            {/* Download Button */}
            <button
              type="button"
              onClick={handleDownload}
              disabled={!docData}
              className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shadow-2xs cursor-pointer disabled:opacity-50"
              title={`Download ${fileName}`}
            >
              {downloaded ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                  <span className="text-emerald-700 hidden sm:inline">Downloaded</span>
                </>
              ) : (
                <>
                  <Download className="w-3.5 h-3.5 text-slate-600" />
                  <span className="hidden sm:inline">Download</span>
                </>
              )}
            </button>

            {/* Close Button */}
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
              title="Close modal (Esc)"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 bg-white">
          {loading && (
            <div className="flex flex-col items-center justify-center h-64 gap-3 text-slate-500">
              <Loader2 className="w-8 h-8 text-[#f05a28] animate-spin" />
              <p className="text-sm font-medium">Loading source document...</p>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-sm">
              <p className="font-semibold mb-1">Failed to retrieve document</p>
              <p className="text-xs text-red-700 leading-relaxed">{error}</p>
            </div>
          )}

          {!loading && !error && docData && (
            <div>
              {/* Context Anchor Notice */}
              {lineRangeStr && (
                <div className="mb-5 p-3 rounded-xl bg-amber-50/80 border border-amber-200 flex items-center justify-between text-xs text-amber-900">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-[#f05a28]">📌 Citation Reference:</span>
                    <span>
                      The grounded answer cited lines <strong className="font-mono">{lineRangeStr}</strong> of this document.
                    </span>
                  </div>
                  <span className="text-[11px] text-amber-700 font-mono hidden sm:inline">
                    {docData.file}
                  </span>
                </div>
              )}

              {/* Document Rendering */}
              {viewMode === 'rendered' ? (
                <div className="max-w-none">
                  {fileName.toLowerCase().endsWith('.kt') || fileName.toLowerCase().endsWith('.kts') ? (
                    <MarkdownRenderer content={`\`\`\`kotlin\n${docData.content}\n\`\`\``} />
                  ) : (
                    <MarkdownRenderer content={docData.content} />
                  )}
                </div>
              ) : (
                <div className="rounded-xl overflow-hidden border border-slate-200 bg-slate-900 text-slate-100 text-xs font-mono p-4 overflow-x-auto leading-relaxed">
                  <pre>{docData.content}</pre>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-5 py-2.5 border-t border-slate-200 bg-slate-50 text-[11px] text-slate-500 shrink-0">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
            <span>Authenticated Document Access • Read-only</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 rounded-md font-medium transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
