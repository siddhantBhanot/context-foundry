import React from 'react';
import {
  Briefcase,
  Building2,
  FileCheck,
  ShieldAlert,
  TrendingUp,
  X,
} from 'lucide-react';
import type { CustomerRelationship } from '@/types';

interface ManagementSummaryModalProps {
  customer: CustomerRelationship;
  isOpen: boolean;
  onClose: () => void;
}

export const ManagementSummaryModal: React.FC<ManagementSummaryModalProps> = ({
  customer,
  isOpen,
  onClose,
}) => {
  if (!isOpen) return null;

  const summary = customer.management_summary;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden">
        
        {/* Header */}
        <div className="bg-slate-900 p-6 text-white flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-white/10 flex items-center justify-center font-black">
              <Building2 className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-white/10 text-[10px] font-bold uppercase tracking-wider text-slate-300">
                <FileCheck className="w-3 h-3 text-amber-400" />
                <span>Executive Continuity Dossier</span>
              </div>
              <h2 className="text-base font-bold text-white">
                Management Relationship Summary: {customer.name}
              </h2>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-white/10 hover:bg-white/20 text-white/80 hover:text-white transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs">
          {summary ? (
            <>
              {/* Snapshot */}
              <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 space-y-1">
                <span className="font-bold text-slate-400 uppercase text-[10px] tracking-wider block">
                  Client & Portfolio Snapshot
                </span>
                <p className="text-slate-800 font-semibold leading-relaxed">{summary.client_snapshot}</p>
                <div className="pt-1 text-[11px] text-slate-500 font-mono">{summary.aum_and_tier}</div>
              </div>

              {/* Handover state */}
              <div className="p-3.5 rounded-2xl bg-blue-50/70 border border-blue-200 space-y-1">
                <span className="font-bold text-blue-800 uppercase text-[10px] tracking-wider flex items-center gap-1">
                  <Briefcase className="w-3.5 h-3.5 text-blue-600" />
                  RM Transition Status
                </span>
                <p className="text-blue-950 font-medium">{summary.rm_handover_status}</p>
                <p className="text-[11px] text-blue-800 pt-0.5">
                  Handover from <strong>{customer.previous_rm_name}</strong> to <strong>{customer.new_rm_name}</strong>.
                </p>
              </div>

              {/* Active Opportunities */}
              <div className="p-3.5 rounded-2xl bg-emerald-50/70 border border-emerald-200 space-y-1.5">
                <span className="font-bold text-emerald-900 uppercase text-[10px] tracking-wider flex items-center gap-1">
                  <TrendingUp className="w-3.5 h-3.5 text-emerald-700" />
                  Active Business Opportunities
                </span>
                <ul className="space-y-1 text-emerald-950">
                  {summary.active_opportunities.map((opp, idx) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-emerald-600 font-bold">•</span>
                      <span>{opp}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Risk & Unresolved */}
              <div className="p-3.5 rounded-2xl bg-rose-50/60 border border-rose-200 space-y-1.5">
                <span className="font-bold text-[#97144d] uppercase text-[10px] tracking-wider flex items-center gap-1">
                  <ShieldAlert className="w-3.5 h-3.5 text-[#97144d]" />
                  Identified Retention Risks & Unresolved Commitments
                </span>
                <ul className="space-y-1 text-slate-800">
                  {summary.risk_and_unresolved.map((r, idx) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-[#97144d] font-bold">•</span>
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Executive Notes */}
              <div className="p-3.5 rounded-2xl bg-amber-50/60 border border-amber-200 space-y-1">
                <span className="font-bold text-amber-900 uppercase text-[10px] tracking-wider block">
                  Leadership Guidance & Next Action
                </span>
                <p className="text-amber-950 italic">{summary.executive_notes}</p>
              </div>
            </>
          ) : (
            <div className="p-8 text-center text-slate-400">
              Generating management summary...
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-100 flex items-center justify-end bg-slate-50 shrink-0">
          <button
            onClick={onClose}
            className="px-5 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold rounded-xl transition-all shadow-xs cursor-pointer"
          >
            Close Summary
          </button>
        </div>

      </div>
    </div>
  );
};
