import React, { useState, useRef } from 'react';
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Cpu,
  HelpCircle,
  Loader2,
  MessageSquare,
  Search,
  Sparkles,
  Tag,
} from 'lucide-react';
import apiClient from '@/lib/api/client';
import MarkdownRenderer from '@/components/chat/MarkdownRenderer';
import type { AskSaathiResponse, CustomerRelationship } from '@/types';

interface AskSaathiDrawerProps {
  customer: CustomerRelationship;
}

const SUGGESTED_QUESTIONS = [
  'Did we promise any concessions for overseas tuition?',
  'What was the customer discussing with the previous RM?',
  'What are the customer’s current priorities?',
  'What are the customer’s communication preferences?',
  'What issues are currently unresolved and what do we owe?',
  'Why was the customer sensitive during the loan review?',
];

export const AskSaathiDrawer: React.FC<AskSaathiDrawerProps> = ({ customer }) => {
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [streamingMeta, setStreamingMeta] = useState<{
    model?: string;
    is_fallback?: boolean;
    evidence?: any[];
    is_commitment?: boolean;
    commitment_type?: string | null;
    drilldown_context?: string | null;
  } | null>(null);
  const [answer, setAnswer] = useState<AskSaathiResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const answerRef = useRef<HTMLDivElement>(null);

  const handleAsk = async (questionText: string) => {
    if (!questionText.trim()) return;
    setIsLoading(true);
    setIsStreaming(false);
    setStreamingText('');
    setStreamingMeta(null);
    setAnswer(null);
    setError(null);
    setQuery(questionText);

    let accumulatedText = '';
    let currentMeta: any = null;

    try {
      await apiClient.askSaathiStream(customer.id, questionText, {
        onMetadata: (meta) => {
          currentMeta = meta;
          setStreamingMeta(meta);
          setIsLoading(false);
          setIsStreaming(true);
        },
        onChunk: (chunk) => {
          accumulatedText += chunk;
          setStreamingText(accumulatedText);
          setIsLoading(false);
          setIsStreaming(true);
        },
        onDone: (done) => {
          setIsStreaming(false);
          setIsLoading(false);
          setAnswer({
            question: questionText,
            answer: done.answer || accumulatedText,
            confidence: 'HIGH',
            evidence: done.evidence || currentMeta?.evidence || [],
            is_commitment: done.is_commitment ?? currentMeta?.is_commitment ?? false,
            commitment_type: done.commitment_type ?? currentMeta?.commitment_type ?? null,
            drilldown_context: done.drilldown_context ?? currentMeta?.drilldown_context ?? null,
            model: done.model || currentMeta?.model,
            is_fallback: done.is_fallback ?? currentMeta?.is_fallback ?? false,
          });
        },
        onError: (err) => {
          setIsStreaming(false);
          setIsLoading(false);
          if (!accumulatedText) {
            setError(err || 'Failed to stream answer from Saathi.');
          }
        },
      });
    } catch (err: any) {
      setIsStreaming(false);
      setIsLoading(false);
      if (!accumulatedText) {
        setError(err?.message || 'Failed to get answer from Saathi.');
      }
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
    }
  };

  // Derive active view state
  const hasAnswer = Boolean(answer || (isStreaming && (streamingText || streamingMeta)));
  const displayContent = answer?.answer ?? streamingText;
  const activeModel = answer?.model ?? streamingMeta?.model;
  const isFallback = Boolean(answer?.is_fallback ?? streamingMeta?.is_fallback);
  const isCommitment = Boolean(answer?.is_commitment ?? streamingMeta?.is_commitment);
  const commitmentType = answer?.commitment_type ?? streamingMeta?.commitment_type;
  const evidenceList = answer?.evidence ?? streamingMeta?.evidence ?? [];
  const drilldownContext = answer?.drilldown_context ?? streamingMeta?.drilldown_context;

  return (
    <div className="bg-white rounded-3xl border border-slate-200/80 p-6 shadow-xs space-y-6">
      
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-purple-100 text-purple-800 flex items-center justify-center font-black text-sm">
            <Sparkles className="w-4 h-4 text-purple-700" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">Ask Saathi — Relationship Intelligence</h3>
            <p className="text-[11px] text-slate-500">
              Grounded strictly in {customer.name}’s historical touchpoints, commitments, and recorded facts.
            </p>
          </div>
        </div>
        <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-purple-50 text-purple-800 border border-purple-200">
          Anti-Hallucination Guardrails Active
        </span>
      </div>

      {/* Search Input */}
      <div className="space-y-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleAsk(query);
          }}
          className="relative flex items-center"
        >
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`Ask anything about ${customer.name} (e.g. 'Did we promise any concessions?')`}
            className="w-full pl-10 pr-24 py-3 bg-slate-50 border border-slate-200 rounded-2xl text-xs text-slate-800 placeholder-slate-400 focus:outline-hidden focus:ring-2 focus:ring-[#97144d]/20 focus:border-[#97144d] transition-all"
          />
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" />
          <button
            type="submit"
            disabled={isLoading || isStreaming || !query.trim()}
            className="absolute right-2 px-4 py-1.5 bg-[#97144d] hover:bg-[#800e3e] text-white text-xs font-bold rounded-xl shadow-xs transition-all flex items-center gap-1 cursor-pointer disabled:opacity-50"
          >
            {isLoading || isStreaming ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <span>Ask</span>}
            <ArrowRight className="w-3 h-3" />
          </button>
        </form>

        {/* Suggested Quick Prompt Chips */}
        <div className="space-y-1.5">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Suggested RM Queries:
          </span>
          <div className="flex items-center gap-1.5 flex-wrap">
            {SUGGESTED_QUESTIONS.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleAsk(q)}
                disabled={isLoading || isStreaming}
                className="px-2.5 py-1 bg-slate-100/80 hover:bg-rose-50 text-slate-700 hover:text-[#97144d] border border-slate-200/60 hover:border-rose-200 rounded-lg text-[11px] font-medium transition-colors cursor-pointer text-left disabled:opacity-50"
              >
                “{q}”
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Initial Loading Spinner */}
      {isLoading && !hasAnswer && (
        <div className="p-8 rounded-2xl bg-slate-50 border border-slate-100 flex flex-col items-center justify-center space-y-2 text-center animate-in fade-in">
          <Loader2 className="w-6 h-6 text-[#97144d] animate-spin" />
          <p className="text-xs font-semibold text-slate-600">
            Consulting customer interaction memory & Bedrock Sonnet 4.6...
          </p>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 flex items-center gap-2.5 text-xs text-rose-800">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Streaming or Completed Answer */}
      {hasAnswer && (
        <div ref={answerRef} className="p-5 rounded-2xl bg-slate-50/80 border border-slate-200/80 space-y-4 animate-in fade-in duration-200">
          
          {/* Answer Header, Model Badge & Distinction Badge */}
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-[#97144d]" />
              <span className="text-xs font-bold text-slate-800">Answer:</span>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              {/* Display LLM Model in Frontend */}
              {activeModel && (
                <div
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold border shadow-2xs ${
                    isFallback
                      ? 'bg-amber-50 text-amber-800 border-amber-300'
                      : 'bg-purple-50 text-purple-800 border-purple-200'
                  }`}
                  title={isFallback ? 'Fallback model activated because primary model was unavailable' : 'Generated via Bedrock Sonnet 4.6'}
                >
                  <Cpu className="w-3.5 h-3.5 shrink-0 text-purple-700" />
                  <span>{activeModel}</span>
                  {isFallback && (
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-200 text-amber-900 uppercase tracking-wider">
                      Fallback
                    </span>
                  )}
                </div>
              )}

              {/* Commitment vs Discussion Distinction Badge */}
              {isCommitment && (
                <div>
                  {commitmentType === 'confirmed_commitment' ? (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-black uppercase tracking-wider">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                      Confirmed Promise / SLA
                    </span>
                  ) : commitmentType === 'discussed_possibility' ? (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[10px] font-black uppercase tracking-wider">
                      <HelpCircle className="w-3 h-3 text-amber-600" />
                      Discussed Possibility (No Promise Made)
                    </span>
                  ) : null}
                </div>
              )}
            </div>
          </div>

          {/* Properly Formatted Markdown Answer */}
          <div className="bg-white p-4.5 rounded-xl border border-slate-200/70 shadow-2xs">
            {displayContent ? (
              <div className="relative">
                <MarkdownRenderer content={displayContent} />
                {isStreaming && (
                  <span className="inline-block w-2 h-4 bg-[#97144d] animate-pulse ml-1 align-middle rounded-xs" />
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2 py-2 text-xs text-slate-400">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-[#97144d]" />
                <span>Connecting to Bedrock Sonnet 4.6...</span>
              </div>
            )}
          </div>

          {/* Inspectable Evidence & Citations */}
          {evidenceList && evidenceList.length > 0 && (
            <div className="space-y-2 pt-1 border-t border-slate-200/60">
              <span className="text-[10px] font-black uppercase text-slate-500 tracking-wider flex items-center gap-1">
                <Tag className="w-3 h-3 text-slate-400" />
                Supporting Historical Evidence ({evidenceList.length}):
              </span>

              <div className="grid grid-cols-1 gap-2">
                {evidenceList.map((ev, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-white border border-slate-200 text-xs text-slate-700 space-y-1 shadow-2xs"
                  >
                    <div className="flex items-center justify-between text-[10px] text-slate-400">
                      <span className="font-bold text-slate-700">
                        {ev.channel} • {ev.rm_name}
                      </span>
                      <span className="font-mono">{ev.date}</span>
                    </div>
                    <p className="text-[11px] text-slate-600 italic bg-slate-50 p-2 rounded-lg border border-slate-100">
                      “{ev.snippet}”
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {drilldownContext && (
            <div className="text-[10px] text-slate-400 text-right">
              {drilldownContext}
            </div>
          )}

        </div>
      )}

    </div>
  );
};
