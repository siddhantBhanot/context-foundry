import React from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Compass,
  Heart,
  MessageCircle,
  PhoneCall,
  ShieldCheck,
  Sparkles,
  X,
  Zap,
} from 'lucide-react';
import type { CustomerRelationship } from '@/types';

interface PreCallBriefModalProps {
  customer: CustomerRelationship;
  isOpen: boolean;
  onClose: () => void;
}

export const PreCallBriefModal: React.FC<PreCallBriefModalProps> = ({
  customer,
  isOpen,
  onClose,
}) => {
  if (!isOpen) return null;

  const brief = customer.pre_call_brief;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-[#97144d] via-[#800e3e] to-[#4a0823] p-6 text-white flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-white/15 backdrop-blur-xs flex items-center justify-center font-black">
              <PhoneCall className="w-5 h-5 text-amber-300" />
            </div>
            <div>
              <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-white/20 text-[10px] font-bold uppercase tracking-wider text-rose-100">
                <Clock className="w-3 h-3 text-amber-300" />
                <span>2-Minute Pre-Call Briefing</span>
              </div>
              <h2 className="text-lg font-bold text-white">
                What Should I Know Before Calling {customer.name}?
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

        {/* Modal Body: 8 Core Pre-Call Dimensions */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs">
          
          {brief ? (
            <>
              {/* 1. Who is this customer? */}
              <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-1">
                <span className="font-bold text-slate-800 uppercase text-[10px] tracking-wider flex items-center gap-1.5 text-[#97144d]">
                  <Sparkles className="w-3.5 h-3.5" />
                  1. Who is this customer?
                </span>
                <p className="text-slate-700 leading-relaxed font-medium">{brief.who_is_customer}</p>
              </div>

              {/* 2. What matters to them? */}
              <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-1.5">
                <span className="font-bold text-slate-800 uppercase text-[10px] tracking-wider flex items-center gap-1.5 text-orange-700">
                  <Heart className="w-3.5 h-3.5" />
                  2. What matters to them?
                </span>
                <ul className="space-y-1 text-slate-700">
                  {brief.what_matters.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-orange-500 font-bold">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* 3. What are we currently discussing? */}
              <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-1.5">
                <span className="font-bold text-slate-800 uppercase text-[10px] tracking-wider flex items-center gap-1.5 text-blue-700">
                  <MessageCircle className="w-3.5 h-3.5" />
                  3. What are we currently discussing?
                </span>
                <ul className="space-y-1 text-slate-700">
                  {brief.current_discussions.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-blue-500 font-bold">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* 4. What did we promise? */}
              <div className="p-3.5 rounded-2xl bg-emerald-50/70 border border-emerald-200 space-y-1.5">
                <span className="font-bold text-emerald-900 uppercase text-[10px] tracking-wider flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-700" />
                  4. What did we promise? (Commitments & Follow-ups)
                </span>
                <ul className="space-y-1 text-emerald-950 font-medium">
                  {brief.what_we_owe.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-emerald-600 font-bold">✓</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* 5. What is unresolved? */}
              <div className="p-3.5 rounded-2xl bg-amber-50/70 border border-amber-200 space-y-1.5">
                <span className="font-bold text-amber-900 uppercase text-[10px] tracking-wider flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
                  5. What is unresolved / sensitive?
                </span>
                <ul className="space-y-1 text-amber-950">
                  {brief.unresolved_issues.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-amber-600 font-bold">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* 6. What should I follow up on? */}
              <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-1.5">
                <span className="font-bold text-slate-800 uppercase text-[10px] tracking-wider flex items-center gap-1.5 text-purple-700">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  6. What should I follow up on?
                </span>
                <ul className="space-y-1 text-slate-700">
                  {brief.follow_up_items.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-purple-600 font-bold">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* 7. Sensitive Nuances */}
              <div className="p-3.5 rounded-2xl bg-rose-50/50 border border-rose-200 space-y-1.5">
                <span className="font-bold text-[#97144d] uppercase text-[10px] tracking-wider flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5" />
                  7. Sensitive Nuances & Taboos
                </span>
                <ul className="space-y-1 text-slate-800">
                  {brief.sensitive_nuances.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-[#97144d] font-bold">⚠️</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* 8. Recommended Conversation Approach */}
              <div className="p-4 rounded-2xl bg-gradient-to-r from-slate-900 to-slate-800 text-white space-y-1.5">
                <span className="font-bold text-amber-300 uppercase text-[10px] tracking-wider flex items-center gap-1.5">
                  <Compass className="w-3.5 h-3.5" />
                  8. Recommended Approach & Tone
                </span>
                <p className="text-xs text-slate-200 leading-relaxed font-medium">
                  {brief.recommended_approach}
                </p>
              </div>
            </>
          ) : (
            <div className="p-8 text-center text-slate-400">
              Generating pre-call briefing for {customer.name}...
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-100 flex items-center justify-end bg-slate-50 shrink-0">
          <button
            onClick={onClose}
            className="px-5 py-2 bg-[#97144d] hover:bg-[#800e3e] text-white text-xs font-bold rounded-xl transition-all shadow-xs cursor-pointer"
          >
            Got it, Ready to Call
          </button>
        </div>

      </div>
    </div>
  );
};
