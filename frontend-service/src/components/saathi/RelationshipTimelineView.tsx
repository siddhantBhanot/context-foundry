import React, { useState } from 'react';
import {
  Briefcase,
  CreditCard,
  GraduationCap,
  History,
  Sparkles,
  UserCheck,
} from 'lucide-react';
import type { CustomerRelationship } from '@/types';

interface RelationshipTimelineViewProps {
  customer: CustomerRelationship;
}

export const RelationshipTimelineView: React.FC<RelationshipTimelineViewProps> = ({
  customer,
}) => {
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  const events = customer.timeline || [];

  const getCategoryIcon = (cat: string) => {
    switch (cat.toLowerCase()) {
      case 'relationship inception':
        return <Sparkles className="w-3.5 h-3.5 text-amber-600" />;
      case 'credit & lending':
        return <CreditCard className="w-3.5 h-3.5 text-emerald-600" />;
      case 'wealth & investment':
        return <Briefcase className="w-3.5 h-3.5 text-blue-600" />;
      case 'family & education':
        return <GraduationCap className="w-3.5 h-3.5 text-purple-600" />;
      case 'transition':
        return <UserCheck className="w-3.5 h-3.5 text-[#97144d]" />;
      default:
        return <History className="w-3.5 h-3.5 text-slate-600" />;
    }
  };

  return (
    <div className="bg-white rounded-3xl border border-slate-200/80 p-6 shadow-xs space-y-6">
      
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center font-black text-sm">
            <History className="w-4 h-4 text-amber-700" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">Relationship Evolution Timeline</h3>
            <p className="text-[11px] text-slate-500">
              How the {customer.tenure_years}-year partnership with {customer.name} evolved across life stages.
            </p>
          </div>
        </div>
        <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
          Relationship-Relevant Events
        </span>
      </div>

      {/* Timeline Tree */}
      <div className="relative pl-6 sm:pl-8 space-y-6 before:absolute before:left-3 sm:before:left-4 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
        {events.map((evt) => {
          const isSelected = selectedEventId === evt.id;

          return (
            <div key={evt.id} className="relative group">
              {/* Timeline marker node */}
              <div
                className={`absolute -left-6 sm:-left-8 top-1.5 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${
                  isSelected
                    ? 'bg-[#97144d] border-[#97144d] text-white shadow-xs'
                    : 'bg-white border-slate-300 group-hover:border-[#97144d] text-slate-600'
                }`}
              >
                {getCategoryIcon(evt.category)}
              </div>

              {/* Event card */}
              <div
                onClick={() => setSelectedEventId(isSelected ? null : evt.id)}
                className={`p-4 rounded-2xl border transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-rose-50/40 border-[#97144d] shadow-sm'
                    : 'bg-slate-50/60 hover:bg-white border-slate-200/80 hover:border-slate-300'
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-black text-[#97144d] font-mono px-2 py-0.5 bg-white rounded-md border border-rose-100">
                      {evt.year}
                    </span>
                    <h4 className="text-xs font-bold text-slate-900">{evt.title}</h4>
                  </div>
                  <span className="text-[10px] text-slate-400 font-mono">{evt.date_display}</span>
                </div>

                <p className="text-xs text-slate-700 leading-relaxed pt-1">{evt.description}</p>

                <div className="flex items-center gap-3 pt-2 text-[10px] text-slate-500 flex-wrap">
                  <span className="px-2 py-0.5 rounded-md bg-white border border-slate-200 font-semibold text-slate-600">
                    {evt.category}
                  </span>
                  {evt.source_channel && (
                    <span className="text-slate-400">Recorded via: {evt.source_channel}</span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

    </div>
  );
};
