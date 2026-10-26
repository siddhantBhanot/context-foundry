import React, { useState } from 'react';
import {
  BookOpen,
  Briefcase,
  CheckCircle2,
  FileText,
  Heart,
  Loader2,
  MessageSquare,
  Sparkles,
  UserCheck,
  X,
  Zap,
} from 'lucide-react';
import type { AddContextRequest, CustomerRelationship } from '@/types';

interface AddContextModalProps {
  customer: CustomerRelationship;
  isOpen: boolean;
  onClose: () => void;
  onSaveContext: (data: AddContextRequest) => Promise<void>;
}

const CATEGORIES = [
  { id: 'Family & Life Stage', label: 'Family & Life Stage', icon: Heart, color: 'text-rose-600 bg-rose-50 border-rose-200' },
  { id: 'Financial & Tax Nuance', label: 'Financial & Tax', icon: Briefcase, color: 'text-emerald-600 bg-emerald-50 border-emerald-200' },
  { id: 'External Advisor / CA', label: 'External Advisor / CA', icon: UserCheck, color: 'text-indigo-600 bg-indigo-50 border-indigo-200' },
  { id: 'Communication & Nuances', label: 'Communication Nuance', icon: MessageSquare, color: 'text-amber-600 bg-amber-50 border-amber-200' },
  { id: 'Operational & Service', label: 'Operational & Service', icon: Zap, color: 'text-purple-600 bg-purple-50 border-purple-200' },
  { id: 'General', label: 'General Note', icon: FileText, color: 'text-slate-600 bg-slate-50 border-slate-200' },
];

const CHANNELS = [
  'In-Person Meeting',
  'Phone Call',
  'WhatsApp Note',
  'Advisor / CA Call',
  'Email / Written',
  'Branch Visit',
];

export const AddContextModal: React.FC<AddContextModalProps> = ({
  customer,
  isOpen,
  onClose,
  onSaveContext,
}) => {
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState(CATEGORIES[0].id);
  const [sourceChannel, setSourceChannel] = useState(CHANNELS[0]);
  const [content, setContent] = useState('');
  const [recordedBy, setRecordedBy] = useState(customer.new_rm_name);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) return;

    setIsSubmitting(true);
    setSuccessMessage(null);
    try {
      await onSaveContext({
        title: title.trim(),
        category,
        content: content.trim(),
        source_channel: sourceChannel,
        recorded_by: recordedBy.trim() || customer.new_rm_name,
      });

      setSuccessMessage('Context saved! Indexed into Saathi Qdrant vector collection and AI Brief updated.');
      setTimeout(() => {
        setSuccessMessage(null);
        setTitle('');
        setContent('');
        onClose();
      }, 1200);
    } catch (err) {
      console.error('Failed to add context:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white w-full max-w-2xl rounded-3xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[92vh]">
        
        {/* Header */}
        <div className="px-6 py-5 bg-gradient-to-r from-rose-900 via-[#97144d] to-pink-900 text-white flex items-center justify-between shrink-0">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded-full bg-white/20 text-[10px] font-black uppercase tracking-wider text-rose-100 flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                Qdrant Vector Memory
              </span>
              <span className="text-xs text-rose-200 font-medium">Customer: {customer.name}</span>
            </div>
            <h2 className="text-base font-bold flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-amber-300" />
              <span>Add Relationship Context</span>
            </h2>
            <p className="text-xs text-rose-100/80">
              Record new nuances, CA advice, or life stage updates. Saathi will vectorize this note and update the AI Brief.
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5 overflow-y-auto flex-1">
          {successMessage && (
            <div className="p-3.5 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs font-semibold flex items-center gap-2 animate-in fade-in">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{successMessage}</span>
            </div>
          )}

          {/* Category Picker */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-800">
              Relationship Dimension / Category
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {CATEGORIES.map((cat) => {
                const Icon = cat.icon;
                const isSelected = category === cat.id;
                return (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setCategory(cat.id)}
                    className={`p-2.5 rounded-2xl border text-left text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
                      isSelected
                        ? 'border-[#97144d] bg-rose-50/80 text-[#97144d] ring-2 ring-[#97144d]/10'
                        : 'border-slate-200 hover:border-slate-300 bg-white text-slate-700'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5 shrink-0" />
                    <span className="truncate">{cat.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Title / Headline */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-800">
              Headline / Topic <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Spoke with client's CA regarding Singapore tax filing and SGD repatriation"
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#97144d]/20 focus:border-[#97144d] text-xs font-medium text-slate-800 placeholder:text-slate-400"
            />
          </div>

          {/* Channel and Recorded By */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-800">
                Source Channel
              </label>
              <select
                value={sourceChannel}
                onChange={(e) => setSourceChannel(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#97144d]/20 focus:border-[#97144d] text-xs font-medium text-slate-800 bg-white cursor-pointer"
              >
                {CHANNELS.map((ch) => (
                  <option key={ch} value={ch}>{ch}</option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-800">
                Recorded By
              </label>
              <input
                type="text"
                value={recordedBy}
                onChange={(e) => setRecordedBy(e.target.value)}
                placeholder="Relationship Manager Name"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#97144d]/20 focus:border-[#97144d] text-xs font-medium text-slate-800"
              />
            </div>
          </div>

          {/* Context Details */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-800 flex items-center justify-between">
              <span>Detailed Context & Discussion Notes <span className="text-rose-500">*</span></span>
              <span className="text-[10px] text-slate-400 font-normal">Will be embedded into Qdrant</span>
            </label>
            <textarea
              required
              rows={4}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Provide exact nuances, client statements, advisor guidance, or family details. The AI Brief and Ask Saathi bot will use this context..."
              className="w-full px-3.5 py-2.5 rounded-2xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#97144d]/20 focus:border-[#97144d] text-xs font-normal text-slate-800 placeholder:text-slate-400 leading-relaxed resize-none"
            />
          </div>

          {/* Explanation Banner */}
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 text-slate-600 text-[11px] leading-relaxed flex items-start gap-2.5">
            <Sparkles className="w-4 h-4 text-[#97144d] shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-slate-800">End-to-End Vectorization:</span>{' '}
              Saving this note stores it in the client memory, embeds it into Qdrant collection{' '}
              <code className="px-1 py-0.5 rounded bg-slate-200 font-mono text-[10px] text-slate-800">saathi_relationship_collection</code>{' '}
              tagged with client ID <code className="px-1 py-0.5 rounded bg-slate-200 font-mono text-[10px] text-slate-800">{customer.id}</code>,
              and re-synthesizes the AI Relationship Brief.
            </div>
          </div>

          {/* Footer Actions */}
          <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:text-slate-800 hover:bg-slate-100 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !title.trim() || !content.trim()}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-rose-900 to-[#97144d] hover:from-rose-800 hover:to-[#7d103f] text-white text-xs font-bold transition-all shadow-md flex items-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Vectorizing & Synthesizing...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                  <span>Save & Update AI Brief</span>
                </>
              )}
            </button>
          </div>
        </form>

      </div>
    </div>
  );
};
