import { useState } from 'react';
import { BookOpen, ChevronDown, ChevronUp, Code2, FileCode } from 'lucide-react';
import type { SourceCitation } from '@/types';
import { DocumentViewerModal } from './DocumentViewerModal';

interface SourceCitationListProps {
  sources: SourceCitation[];
  service?: string;
}

export function SourceCitationList({ sources, service }: SourceCitationListProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [activeDoc, setActiveDoc] = useState<{
    service: string;
    file: string;
    startLine?: number;
    endLine?: number;
  } | null>(null);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="pt-3 border-t border-slate-200/80">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
          <span>Verified Citations ({sources.length})</span>
        </span>
      </div>

      <div className="flex flex-col gap-2">
        {sources.map((src, i) => {
          const isExpanded = expandedIndex === i;
          const fileName = src.file.split('/').pop() || src.file;
          const isKotlin =
            fileName.endsWith('.kt') ||
            fileName.endsWith('.kts') ||
            src.doc_type === 'kotlin' ||
            src.docType === 'Kotlin Source';
          const isDoc =
            !isKotlin &&
            (fileName.endsWith('.md') ||
              fileName.endsWith('.markdown') ||
              fileName.endsWith('.txt') ||
              fileName.endsWith('.rst') ||
              src.doc_type === 'markdown');
          const endpoint = src.endpoint;
          const className = src.class_name || src.class;
          const startLine = src.start_line ?? src.lineNumber;
          const endLine = src.end_line;
          const lineStr = startLine
            ? endLine && endLine !== startLine
              ? `L${startLine}-${endLine}`
              : `L${startLine}`
            : null;
          const snippet = src.snippet || src.contentSnippet;

          return (
            <div
              key={i}
              className="rounded-xl border border-slate-200 bg-white shadow-2xs overflow-hidden transition-all hover:border-slate-300"
            >
              <div
                onClick={() => setExpandedIndex(isExpanded ? null : i)}
                className="flex items-center justify-between px-3 py-2 cursor-pointer select-none bg-slate-50/50 hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  {/* File Icon */}
                  <div className="w-5 h-5 rounded-md flex items-center justify-center shrink-0">
                    {isKotlin ? (
                      <FileCode className="w-3.5 h-3.5 text-[#f05a28]" />
                    ) : (
                      <BookOpen className="w-3.5 h-3.5 text-indigo-500" />
                    )}
                  </div>

                  {/* File Name & Path */}
                  <span
                    className="font-mono text-xs font-semibold text-slate-800 truncate"
                    title={src.file}
                  >
                    {fileName}
                  </span>

                  {/* Line numbers pill */}
                  {lineStr && (
                    <span className="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-100 text-slate-600 border border-slate-200">
                      {lineStr}
                    </span>
                  )}

                  {/* REST endpoint pill (for code files) */}
                  {endpoint && (
                    <span className="shrink-0 hidden sm:inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                      <Code2 className="w-2.5 h-2.5" />
                      <span>{endpoint}</span>
                    </span>
                  )}

                  {/* Class name pill (for code files) */}
                  {className && (
                    <span className="shrink-0 hidden md:inline-flex px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-orange-50 text-[#f05a28] border border-orange-200 truncate max-w-[160px]">
                      {className}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2 pl-2">
                  {/* View Document Button (Only for Documentation files, NOT for Code files) */}
                  {isDoc && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setActiveDoc({
                          service: src.service || service || 'income-assessment-service',
                          file: src.file,
                          startLine,
                          endLine,
                        });
                      }}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium text-[#f05a28] bg-orange-50 hover:bg-orange-100 border border-orange-200 transition-colors cursor-pointer shadow-2xs shrink-0"
                      title="View full source document in browser"
                    >
                      <BookOpen className="w-3 h-3" />
                      <span>View Doc</span>
                    </button>
                  )}

                  {/* Snippet expand chevron */}
                  <div className="text-slate-400">
                    {snippet &&
                      (isExpanded ? (
                        <ChevronUp className="w-3.5 h-3.5" />
                      ) : (
                        <ChevronDown className="w-3.5 h-3.5" />
                      ))}
                  </div>
                </div>
              </div>

              {/* Expandable Snippet Preview */}
              {isExpanded && snippet && (
                <div className="px-3 py-2.5 bg-slate-900 text-slate-100 text-xs font-mono border-t border-slate-200 overflow-x-auto">
                  <div className="text-[10px] text-slate-400 mb-1 flex items-center justify-between">
                    <span className="truncate max-w-[300px] sm:max-w-md">File: {src.file}</span>
                    <div className="flex items-center gap-3 shrink-0">
                      {lineStr && <span>Lines: {lineStr}</span>}
                      {isDoc && (
                        <button
                          type="button"
                          onClick={() =>
                            setActiveDoc({
                              service: src.service || service || 'income-assessment-service',
                              file: src.file,
                              startLine,
                              endLine,
                            })
                          }
                          className="text-[#f05a28] hover:text-orange-300 font-sans font-medium transition-colors underline cursor-pointer"
                        >
                          View Full Document →
                        </button>
                      )}
                    </div>
                  </div>
                  <pre className="text-[11px] leading-relaxed text-slate-200 whitespace-pre-wrap">
                    {snippet}
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Document Viewer Modal */}
      {activeDoc && (
        <DocumentViewerModal
          isOpen={!!activeDoc}
          onClose={() => setActiveDoc(null)}
          service={activeDoc.service}
          file={activeDoc.file}
          startLine={activeDoc.startLine}
          endLine={activeDoc.endLine}
        />
      )}
    </div>
  );
}
