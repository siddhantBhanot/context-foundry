import React, { useState } from 'react';
import {
  AlertCircle,
  Calendar,
  Check,
  HelpCircle,
  ShieldCheck,
  User,
} from 'lucide-react';
import apiClient from '@/lib/api/client';
import type { CommitmentItem, CommitmentStatus, CustomerRelationship } from '@/types';

interface CommitmentsDashboardProps {
  customer: CustomerRelationship;
  onRefreshCustomer: () => Promise<void>;
}

export const CommitmentsDashboard: React.FC<CommitmentsDashboardProps> = ({
  customer,
  onRefreshCustomer,
}) => {
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<'all' | 'confirmed' | 'discussed'>('all');

  const commitments = customer.commitments || [];

  const handleToggleStatus = async (item: CommitmentItem) => {
    setUpdatingId(item.id);
    const nextStatus: CommitmentStatus =
      item.status === 'completed'
        ? 'pending'
        : item.status === 'pending'
        ? 'in_progress'
        : 'completed';

    try {
      await apiClient.updateSaathiCommitment(customer.id, item.id, nextStatus);
      await onRefreshCustomer();
    } catch (err) {
      console.error('Failed to update commitment:', err);
    } finally {
      setUpdatingId(null);
    }
  };

  const filteredItems = commitments.filter((item) => {
    if (activeFilter === 'confirmed') return item.commitment_type === 'confirmed_commitment';
    if (activeFilter === 'discussed') return item.commitment_type === 'discussed_possibility';
    return true;
  });

  const confirmedCount = commitments.filter((c) => c.commitment_type === 'confirmed_commitment').length;
  const discussedCount = commitments.filter((c) => c.commitment_type === 'discussed_possibility').length;

  return (
    <div className="bg-white rounded-3xl border border-slate-200/80 p-6 shadow-xs space-y-6">
      
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#97144d]" />
            <span>What Do We Owe {customer.name}?</span>
          </h3>
          <p className="text-[11px] text-slate-500">
            Explicit tracking of promises and follow-ups made during previous interactions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center rounded-xl bg-slate-100 p-0.5 text-xs font-semibold">
            <button
              onClick={() => setActiveFilter('all')}
              className={`px-3 py-1 rounded-lg transition-all cursor-pointer ${
                activeFilter === 'all'
                  ? 'bg-white text-slate-900 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              All ({commitments.length})
            </button>
            <button
              onClick={() => setActiveFilter('confirmed')}
              className={`px-3 py-1 rounded-lg transition-all cursor-pointer ${
                activeFilter === 'confirmed'
                  ? 'bg-white text-emerald-800 shadow-2xs'
                  : 'text-slate-600 hover:text-emerald-800'
              }`}
            >
              Confirmed Promises ({confirmedCount})
            </button>
            <button
              onClick={() => setActiveFilter('discussed')}
              className={`px-3 py-1 rounded-lg transition-all cursor-pointer ${
                activeFilter === 'discussed'
                  ? 'bg-white text-amber-800 shadow-2xs'
                  : 'text-slate-600 hover:text-amber-800'
              }`}
            >
              Discussed ({discussedCount})
            </button>
          </div>
        </div>
      </div>

      {/* Core Principle Notice */}
      <div className="p-3.5 rounded-2xl bg-amber-50/60 border border-amber-200/70 text-xs text-amber-900 flex items-start gap-2.5">
        <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <strong className="font-bold block">Strict Commitment Distinction Principle:</strong>
          Saathi clearly distinguishes between a <strong>Confirmed Commitment</strong> (a binding promise or SLA recorded by the previous RM/bank) and <strong>Something Merely Discussed or Explored</strong>. We never treat a suggestion as a confirmed promise.
        </div>
      </div>

      {/* Commitments List */}
      <div className="space-y-3">
        {filteredItems.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-400 bg-slate-50 rounded-2xl border border-slate-200">
            No commitments matching this filter.
          </div>
        ) : (
          filteredItems.map((item) => {
            const isDone = item.status === 'completed';
            const isConfirmed = item.commitment_type === 'confirmed_commitment';
            const isUpdating = updatingId === item.id;

            return (
              <div
                key={item.id}
                className={`p-4 rounded-2xl border transition-all ${
                  isDone
                    ? 'bg-slate-50/70 border-slate-200/70 opacity-60'
                    : isConfirmed
                    ? 'bg-rose-50/20 border-rose-200/80 hover:border-rose-300'
                    : 'bg-amber-50/20 border-amber-200/80 hover:border-amber-300'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    {/* Checkbox trigger */}
                    <button
                      onClick={() => handleToggleStatus(item)}
                      disabled={isUpdating}
                      className={`w-5 h-5 mt-0.5 rounded-lg flex items-center justify-center shrink-0 border transition-all cursor-pointer ${
                        isDone
                          ? 'bg-emerald-600 border-emerald-600 text-white'
                          : 'border-slate-300 bg-white hover:border-[#97144d]'
                      }`}
                      title={isDone ? 'Mark Pending' : 'Mark Completed'}
                    >
                      {isDone && <Check className="w-3.5 h-3.5" />}
                    </button>

                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4
                          className={`text-xs font-bold leading-tight ${
                            isDone ? 'line-through text-slate-500' : 'text-slate-900'
                          }`}
                        >
                          {item.title}
                        </h4>

                        {/* Type badge */}
                        {isConfirmed ? (
                          <span className="inline-flex items-center gap-1 text-[9px] font-black uppercase px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-800">
                            <ShieldCheck className="w-3 h-3" />
                            Confirmed Commitment
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[9px] font-black uppercase px-2 py-0.5 rounded-md bg-amber-100 text-amber-800">
                            <HelpCircle className="w-3 h-3" />
                            Discussed Possibility
                          </span>
                        )}

                        {/* Status badge */}
                        <span
                          className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded-md ${
                            item.status === 'completed'
                              ? 'bg-slate-100 text-slate-600'
                              : item.status === 'in_progress'
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-rose-100 text-[#97144d]'
                          }`}
                        >
                          {item.status.replace('_', ' ')}
                        </span>
                      </div>

                      <p className="text-xs text-slate-700 leading-relaxed">{item.details}</p>

                      {/* Evidence Snippet */}
                      {item.evidence_snippet && (
                        <div className="text-[11px] text-slate-600 bg-white p-2 rounded-xl border border-slate-200/80 italic">
                          <span className="font-semibold text-slate-700 not-italic">CRM Evidence: </span>
                          “{item.evidence_snippet}”
                        </div>
                      )}

                      {/* Metadata row */}
                      <div className="flex items-center gap-4 pt-1 text-[10px] text-slate-400 font-medium">
                        <span className="flex items-center gap-1">
                          <User className="w-3 h-3 text-slate-400" />
                          <span>Committed by: <strong className="text-slate-700">{item.committed_by}</strong></span>
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3 text-slate-400" />
                          <span>Date: {item.committed_on}</span>
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Urgency Pill */}
                  <span
                    className={`text-[9px] font-black uppercase px-2 py-0.5 rounded-full shrink-0 ${
                      item.urgency === 'high'
                        ? 'bg-rose-100 text-rose-800'
                        : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {item.urgency} Urgency
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>

    </div>
  );
};
