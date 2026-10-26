import { ArrowLeft, CheckCircle2 } from 'lucide-react';
import type { CourseDetail } from '@/types';

interface CurriculumSidebarProps {
  course: CourseDetail;
  activeLessonId: string;
  onSelectLesson: (lessonId: string) => void;
  onBackToCatalog: () => void;
}

export function CurriculumSidebar({
  course,
  activeLessonId,
  onSelectLesson,
  onBackToCatalog,
}: CurriculumSidebarProps) {
  const completedCount = course.enrollment?.completed_lessons.length || 0;
  const totalLessons = course.lessons.length || 1;
  const progressPercent = Math.min(100, Math.round((completedCount / totalLessons) * 100));

  return (
    <aside className="w-80 md:w-88 border-r border-slate-100 bg-slate-50/50 flex flex-col h-full shrink-0">
      {/* Sidebar Header */}
      <div className="p-5 border-b border-slate-100 space-y-3 bg-white">
        <button
          onClick={onBackToCatalog}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          All Courses
        </button>

        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-[#f05a28] bg-orange-50 border border-orange-200/60 px-2 py-0.5 rounded-full">
            {course.target_service}
          </span>
          <h2 className="text-sm font-bold text-slate-900 mt-1.5 line-clamp-1">
            {course.title}
          </h2>
        </div>

        {/* Progress Bar */}
        <div className="space-y-1.5 pt-1">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-500 font-medium">Curriculum Progress</span>
            <span className="font-bold text-slate-800">{progressPercent}%</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden border border-slate-200/60">
            <div
              className="bg-[#f05a28] h-full rounded-full transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <p className="text-[10px] text-slate-400">
            {completedCount} of {totalLessons} lessons completed
          </p>
        </div>
      </div>

      {/* Lesson List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        {course.lessons.map((lesson, idx) => {
          const isCompleted = lesson.status === 'completed';
          const isActive = lesson.id === activeLessonId;

          return (
            <button
              key={lesson.id}
              onClick={() => onSelectLesson(lesson.id)}
              className={`w-full text-left p-3 rounded-xl transition-all cursor-pointer flex items-start gap-3 border ${
                isActive
                  ? 'bg-white border-[#f05a28] shadow-xs text-slate-900'
                  : isCompleted
                  ? 'bg-white/60 hover:bg-white border-transparent hover:border-slate-200/60 text-slate-700'
                  : 'hover:bg-white/40 border-transparent text-slate-500'
              }`}
            >
              {/* Step indicator */}
              <div className="mt-0.5 shrink-0">
                {isCompleted ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                ) : isActive ? (
                  <div className="w-4 h-4 rounded-full bg-[#f05a28] text-white flex items-center justify-center text-[10px] font-bold ring-2 ring-orange-200">
                    {idx + 1}
                  </div>
                ) : (
                  <div className="w-4 h-4 rounded-full bg-slate-200 text-slate-600 flex items-center justify-center text-[10px] font-semibold">
                    {idx + 1}
                  </div>
                )}
              </div>

              {/* Title & Preview */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-1">
                  <span
                    className={`text-xs font-semibold truncate ${
                      isActive ? 'text-[#f05a28]' : 'text-slate-800'
                    }`}
                  >
                    {lesson.title}
                  </span>
                  {isActive && (
                    <span className="w-1.5 h-1.5 rounded-full bg-[#f05a28] animate-pulse shrink-0" />
                  )}
                </div>
                {lesson.summary && (
                  <p className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">
                    {lesson.summary}
                  </p>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
