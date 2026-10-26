import {
  Award,
  CheckCircle2,
  MessageSquare,
  X,
} from 'lucide-react';
import type { CourseDetail } from '@/types';

interface CourseCompletionModalProps {
  isOpen: boolean;
  onClose: () => void;
  course: CourseDetail;
  onExploreInChat: (service: string) => void;
}

export function CourseCompletionModal({
  isOpen,
  onClose,
  course,
  onExploreInChat,
}: CourseCompletionModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl max-w-lg w-full p-8 shadow-2xl border border-slate-100 space-y-6 animate-in zoom-in-95 duration-300 relative">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Celebration Header */}
        <div className="text-center space-y-3">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-amber-400 to-[#f05a28] text-white flex items-center justify-center mx-auto shadow-md">
            <Award className="w-8 h-8" />
          </div>
          <div className="space-y-1">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 text-xs font-bold uppercase tracking-wide">
              <CheckCircle2 className="w-3.5 h-3.5" />
              100% Curriculum Completed
            </div>
            <h2 className="text-xl md:text-2xl font-bold text-slate-900">
              Knowledge Cafe Complete ✓
            </h2>
            <p className="text-xs md:text-sm text-slate-600 max-w-md mx-auto">
              You have completed the full KT for{' '}
              <span className="font-semibold text-slate-800">{course.title}</span>.
            </p>
          </div>
        </div>

        {/* Completed Lessons Checklist */}
        <div className="bg-slate-50 rounded-2xl p-4 border border-slate-100 space-y-2.5 max-h-56 overflow-y-auto">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-1">
            Mastered Lessons ({course.lessons.length})
          </p>
          <div className="space-y-1.5">
            {course.lessons.map((lesson) => (
              <div
                key={lesson.id}
                className="flex items-center gap-2 text-xs font-medium text-slate-700 bg-white p-2.5 rounded-xl border border-slate-200/60"
              >
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span className="truncate">{lesson.title}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Action CTAs */}
        <div className="space-y-2.5 pt-2">
          <button
            onClick={() => onExploreInChat(course.target_service)}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-[#f05a28] hover:bg-[#d94819] text-white text-xs md:text-sm font-semibold shadow-xs transition-transform active:scale-95 cursor-pointer"
          >
            <MessageSquare className="w-4 h-4" />
            Explore in Chat Assistant →
          </button>
          <button
            onClick={onClose}
            className="w-full py-2.5 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            Review Course Material
          </button>
        </div>
      </div>
    </div>
  );
}
