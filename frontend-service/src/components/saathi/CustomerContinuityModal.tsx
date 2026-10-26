import React, { useState } from 'react';
import {
  AlertCircle,
  ArchiveX,
  Check,
  CheckCircle2,
  Edit3,
  HelpCircle,
  Phone,
  Send,
  UserCheck,
  X,
} from 'lucide-react';
import apiClient from '@/lib/api/client';
import type { CustomerFact, CustomerRelationship } from '@/types';

interface CustomerContinuityModalProps {
  customer: CustomerRelationship;
  isOpen: boolean;
  onClose: () => void;
  onSubmitFeedback: (notes: string) => Promise<void>;
  onFactValidated?: () => Promise<void>;
}

export const CustomerContinuityModal: React.FC<CustomerContinuityModalProps> = ({
  customer,
  isOpen,
  onClose,
  onSubmitFeedback,
  onFactValidated,
}) => {
  const [customNotes, setCustomNotes] = useState(
    customer.feedback?.customer_notes || ''
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(customer.feedback?.has_verified || false);
  const [error, setError] = useState<string | null>(null);

  // Per-fact editing state
  const [editingFactId, setEditingFactId] = useState<string | null>(null);
  const [editedFactText, setEditedFactText] = useState('');
  const [validatingFactId, setValidatingFactId] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleFactAction = async (
    factId: string,
    action: 'confirm' | 'update' | 'mark_irrelevant',
    text?: string
  ) => {
    setValidatingFactId(factId);
    try {
      await apiClient.validateSaathiFact(customer.id, factId, action, text);
      setEditingFactId(null);
      setEditedFactText('');
      if (onFactValidated) {
        await onFactValidated();
      }
    } catch (err: any) {
      console.error('Failed to validate fact:', err);
    } finally {
      setValidatingFactId(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customNotes.trim()) {
      setError('Please add a note or confirmation for your new Relationship Manager.');
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmitFeedback(customNotes);
      setSubmitted(true);
    } catch (err: any) {
      setError(err.message || 'Failed to submit response');
    } finally {
      setIsSubmitting(false);
    }
  };

  const facts = customer.facts || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-3 sm:p-4 overflow-y-auto animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl border border-slate-100 shadow-2xl max-w-2xl w-full my-6 overflow-hidden flex flex-col">
        
        {/* Header with Burgundy styling */}
        <div className="bg-gradient-to-br from-[#97144d] via-[#800e3e] to-[#4a0823] text-white p-6 sm:p-7 relative">
          <button
            onClick={onClose}
            className="absolute top-5 right-5 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white/80 hover:text-white transition-colors cursor-pointer"
            title="Close"
          >
            <X className="w-4 h-4" />
          </button>

          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] font-bold tracking-widest uppercase bg-white/15 px-2.5 py-0.5 rounded-full text-white/90 border border-white/20">
              Saathi • Client Context Validation
            </span>
            <span className="text-[10px] font-semibold text-rose-200">
              {customer.tier}
            </span>
          </div>

          <h2 className="text-xl sm:text-2xl font-black tracking-tight text-white mb-1.5">
            “Here is what we understand about you.”
          </h2>
          <p className="text-xs text-rose-100/90 leading-relaxed max-w-lg">
            When your RM changes, your relationship stays. Review Saathi’s memory of your priorities. You remain the sole authority over your personal context.
          </p>
        </div>

        {/* Scrollable Content */}
        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto bg-slate-50/40">
          
          {/* Handover Introduction Card */}
          <div className="p-4 rounded-2xl bg-white border border-slate-200/80 shadow-2xs space-y-3">
            <div className="flex items-center justify-between text-xs pb-2 border-b border-slate-100">
              <span className="text-slate-500 font-medium">Relationship Manager Handover</span>
              <span className="text-[11px] font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded-md">
                Client ID: {customer.account_number_masked}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 space-y-1">
                <span className="text-[10px] font-semibold uppercase text-slate-400 block">
                  Outgoing RM
                </span>
                <p className="font-bold text-slate-800">{customer.previous_rm_name}</p>
                <p className="text-[11px] text-slate-500 leading-snug">{customer.transfer_reason}</p>
              </div>

              <div className="p-2.5 rounded-xl bg-rose-50/60 border border-rose-100 space-y-1">
                <span className="text-[10px] font-semibold uppercase text-[#97144d] block font-bold">
                  Your New Assigned RM
                </span>
                <p className="font-bold text-[#97144d]">{customer.new_rm_name}</p>
                <p className="text-[11px] text-slate-600">{customer.new_rm_role}</p>
                <div className="flex items-center gap-2 pt-1 text-[11px] text-slate-500">
                  <span className="flex items-center gap-1 font-mono">
                    <Phone className="w-3 h-3 text-[#97144d]" /> {customer.new_rm_phone}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Granular Relationship Context Validation (Section 14 & 15) */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs font-bold text-slate-800">
              <div className="flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-[#97144d]" />
                <span>Relationship Memory Validation</span>
              </div>
              <span className="text-[11px] text-slate-500 font-normal">
                Confirm, update, or mark outdated
              </span>
            </div>

            <div className="space-y-2.5">
              {facts.map((fact: CustomerFact) => {
                const isEditing = editingFactId === fact.id;
                const isValidating = validatingFactId === fact.id;

                return (
                  <div
                    key={fact.id}
                    className={`p-3.5 rounded-2xl border transition-all ${
                      fact.status === 'no_longer_relevant'
                        ? 'bg-slate-100 border-slate-200 opacity-50'
                        : fact.status === 'updated'
                        ? 'bg-amber-50/60 border-amber-200'
                        : 'bg-white border-slate-200 shadow-2xs'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-md bg-slate-100 text-slate-600">
                            {fact.category}
                          </span>
                          {fact.status === 'confirmed' && (
                            <span className="text-[10px] font-bold text-emerald-700 flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Confirmed
                            </span>
                          )}
                          {fact.status === 'updated' && (
                            <span className="text-[10px] font-bold text-amber-700 flex items-center gap-1">
                              <Edit3 className="w-3 h-3 text-amber-600" /> Customer Updated
                            </span>
                          )}
                          {fact.status === 'no_longer_relevant' && (
                            <span className="text-[10px] font-bold text-slate-500 line-through">
                              No Longer Relevant
                            </span>
                          )}
                        </div>

                        <p className={`text-xs text-slate-800 leading-relaxed font-medium ${
                          fact.status === 'no_longer_relevant' ? 'line-through text-slate-400' : ''
                        }`}>
                          {fact.statement}
                        </p>

                        {fact.updated_note && (
                          <div className="text-[11px] text-amber-900 bg-amber-100/60 p-2 rounded-xl border border-amber-200/80">
                            <strong>Your Update:</strong> {fact.updated_note}
                          </div>
                        )}
                      </div>

                      {/* 3 Interactive Decision Buttons */}
                      <div className="flex items-center gap-1.5 shrink-0 pt-0.5">
                        <button
                          onClick={() => handleFactAction(fact.id, 'confirm')}
                          disabled={isValidating}
                          className="px-2.5 py-1 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 text-[10px] font-bold transition-colors cursor-pointer flex items-center gap-1"
                          title="Confirm this is correct"
                        >
                          <Check className="w-3 h-3 text-emerald-600" />
                          <span>Correct</span>
                        </button>

                        <button
                          onClick={() => {
                            setEditingFactId(fact.id);
                            setEditedFactText(fact.statement);
                          }}
                          disabled={isValidating}
                          className="px-2.5 py-1 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 text-[10px] font-bold transition-colors cursor-pointer flex items-center gap-1"
                          title="Update or clarify this item"
                        >
                          <Edit3 className="w-3 h-3 text-amber-600" />
                          <span>Update</span>
                        </button>

                        <button
                          onClick={() => handleFactAction(fact.id, 'mark_irrelevant')}
                          disabled={isValidating}
                          className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 border border-slate-200 text-[10px] font-bold transition-colors cursor-pointer flex items-center gap-1"
                          title="Mark as no longer relevant"
                        >
                          <ArchiveX className="w-3 h-3 text-slate-500" />
                          <span>Outdated</span>
                        </button>
                      </div>
                    </div>

                    {/* Inline Editor if Update clicked */}
                    {isEditing && (
                      <div className="mt-3 p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                        <span className="text-[10px] font-bold text-slate-700 block">
                          Provide updated details for your RM:
                        </span>
                        <input
                          type="text"
                          value={editedFactText}
                          onChange={(e) => setEditedFactText(e.target.value)}
                          className="w-full text-xs p-2 bg-white border border-slate-200 rounded-lg focus:outline-hidden focus:ring-1 focus:ring-[#97144d]"
                          placeholder="Enter current status or update..."
                        />
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => setEditingFactId(null)}
                            className="px-2.5 py-1 text-[10px] text-slate-500 hover:text-slate-700"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleFactAction(fact.id, 'update', editedFactText)}
                            className="px-3 py-1 text-[10px] font-bold bg-[#97144d] text-white rounded-lg hover:bg-[#800e3e]"
                          >
                            Save Update
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Customer Confirmation Note Form */}
          <form onSubmit={handleSubmit} className="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-900">
              <HelpCircle className="w-4 h-4 text-[#97144d]" />
              <span>Is there anything else we missed? Tell {customer.new_rm_name.split(' ')[0]}:</span>
            </div>

            <textarea
              value={customNotes}
              onChange={(e) => setCustomNotes(e.target.value)}
              placeholder="e.g. Please also note that I will be traveling to London next week, or my parents need assistance with tax filing..."
              rows={3}
              className="w-full text-xs p-3 rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-[#97144d]/30 focus:border-[#97144d] bg-slate-50/50 resize-none"
            />

            {error && (
              <div className="flex items-center gap-2 text-xs text-rose-600 bg-rose-50 p-2 rounded-xl border border-rose-100">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {submitted && (
              <div className="flex items-center gap-2 text-xs text-emerald-700 bg-emerald-50 p-2.5 rounded-xl border border-emerald-200">
                <Check className="w-3.5 h-3.5 shrink-0" />
                <span className="font-semibold">
                  Thank you! Your inputs have been verified and synced directly with {customer.new_rm_name}.
                </span>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 px-4 bg-[#97144d] hover:bg-[#800e3e] text-white text-xs font-bold rounded-xl shadow-xs transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
            >
              {isSubmitting ? (
                <span>Syncing with Saathi Continuity Engine...</span>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  <span>Confirm & Update Relationship Memory</span>
                </>
              )}
            </button>
          </form>

        </div>

      </div>
    </div>
  );
};
