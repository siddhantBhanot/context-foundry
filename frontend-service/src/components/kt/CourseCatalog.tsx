import { useState } from 'react';
import {
  CheckCircle2,
  Clock,
  Compass,
  GraduationCap,
  Layers,
  Play,
  RotateCcw,
  Search,
} from 'lucide-react';
import type { CourseSummary } from '@/types';

interface CourseCatalogProps {
  courses: CourseSummary[];
  isLoading: boolean;
  userRole?: 'developer' | 'banking_staff';
  onSelectCourse: (courseId: string) => void;
  onRestartCourse?: (courseId: string) => void;
}

export function CourseCatalog({ courses, isLoading, userRole, onSelectCourse, onRestartCourse }: CourseCatalogProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const isBanking = userRole === 'banking_staff';

  const roleFilteredCourses = courses.filter((c) => {
    if (!c.group) return true;
    return isBanking ? c.group === 'banking' : c.group === 'technical';
  });

  const filteredCourses = roleFilteredCourses.filter((c) => {
    const q = searchQuery.toLowerCase();
    return (
      c.title.toLowerCase().includes(q) ||
      c.description.toLowerCase().includes(q) ||
      c.target_service.toLowerCase().includes(q) ||
      c.domain.toLowerCase().includes(q)
    );
  });

  const inProgressCourse = roleFilteredCourses.find(
    (c) => c.enrollment && !c.enrollment.is_completed && c.enrollment.overall_progress > 0
  );

  return (
    <div className="flex-1 overflow-y-auto px-6 md:px-12 py-8 max-w-5xl mx-auto w-full space-y-8 animate-in fade-in duration-300">
      {/* Hero Welcome Banner */}
      <div className={`relative overflow-hidden rounded-3xl bg-gradient-to-br ${
        isBanking
          ? 'from-slate-900 via-rose-950/40 to-slate-900 border-rose-900/30'
          : 'from-slate-900 via-slate-800 to-slate-900 border-slate-700/50'
      } text-white p-8 md:p-10 shadow-lg border`}>
        <div className={`absolute top-0 right-0 -mt-8 -mr-8 w-64 h-64 ${
          isBanking ? 'bg-[#97144d]/20' : 'bg-[#f05a28]/15'
        } rounded-full blur-3xl pointer-events-none`} />
        <div className="relative z-10 max-w-2xl space-y-3">
          <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-xs font-semibold ${
            isBanking ? 'text-pink-300' : 'text-orange-300'
          } tracking-wide uppercase`}>
            <GraduationCap className={`w-4 h-4 ${isBanking ? 'text-pink-400' : 'text-[#f05a28]'}`} />
            Knowledge Cafe · {isBanking ? 'Banking & Wealth Management' : 'Engineering & Dev'}
          </div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white">
            {isBanking ? 'Banking & Wealth Knowledge Transfer' : 'Engineering Knowledge Transfer'}
          </h1>
          <p className="text-slate-300 text-sm md:text-base leading-relaxed">
            {isBanking
              ? 'Curated professional masterclasses on NRI wealth advisory, retail credit underwriting, and regulatory compliance workflows.'
              : 'Curated, structured onboarding masterclasses. Step through end-to-end architectures, business rule engines, and verified code paths.'}
          </p>
        </div>
      </div>

      {/* Continue Learning Card (if course in progress) */}
      {inProgressCourse && inProgressCourse.enrollment && (
        <div className={`bg-gradient-to-r ${
          isBanking
            ? 'from-pink-500/10 via-rose-500/5 border-pink-200/80'
            : 'from-orange-500/10 via-amber-500/5 border-orange-200/80'
        } to-transparent border rounded-2xl p-6 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4`}>
          <div className="space-y-1.5 flex-1">
            <div className="flex items-center gap-2">
              <span className={`text-[11px] font-bold uppercase tracking-wider ${
                isBanking ? 'text-[#97144d] bg-pink-100/70' : 'text-[#f05a28] bg-orange-100/70'
              } px-2.5 py-0.5 rounded-full`}>
                Continue Learning
              </span>
              <span className="text-xs text-slate-500 font-medium">
                {inProgressCourse.enrollment.overall_progress}% completed
              </span>
            </div>
            <h3 className="text-base md:text-lg font-bold text-slate-900">
              {inProgressCourse.title}
            </h3>
            <div className="w-full max-w-md bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200/60">
              <div
                className={`${isBanking ? 'bg-[#97144d]' : 'bg-[#f05a28]'} h-full rounded-full transition-all duration-500`}
                style={{ width: `${inProgressCourse.enrollment.overall_progress}%` }}
              />
            </div>
          </div>
          <button
            onClick={() => onSelectCourse(inProgressCourse.id)}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl ${
              isBanking ? 'bg-[#97144d] hover:bg-[#800f40]' : 'bg-[#f05a28] hover:bg-[#d94819]'
            } text-white text-sm font-semibold shadow-xs transition-transform active:scale-95 cursor-pointer shrink-0`}
          >
            <Play className="w-4 h-4 fill-white" />
            Resume Course
          </button>
        </div>
      )}

      {/* Search & Filter Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 pt-2">
        <div>
          <h2 className="text-lg font-bold text-slate-900 tracking-tight">
            {isBanking ? 'Banking & Management Courses' : 'Engineering Courses'}
          </h2>
          <p className="text-xs text-slate-500">
            {isBanking
              ? 'Select a banking discipline to start an interactive KT walkthrough'
              : 'Select a service to start an interactive KT walkthrough'}
          </p>
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder={isBanking ? "Search by title, domain..." : "Search by title, service..."}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={`w-full pl-9 pr-4 py-2 text-xs rounded-xl bg-slate-50 border border-slate-200 focus:outline-none ${
              isBanking ? 'focus:border-[#97144d]' : 'focus:border-[#f05a28]'
            } focus:bg-white transition-colors`}
          />
        </div>
      </div>

      {/* Course Cards Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {[1, 2].map((i) => (
            <div
              key={i}
              className="h-56 rounded-2xl bg-slate-50 border border-slate-100 animate-pulse p-6 space-y-4"
            >
              <div className="h-4 bg-slate-200 rounded w-1/3" />
              <div className="h-6 bg-slate-200 rounded w-3/4" />
              <div className="h-12 bg-slate-200 rounded w-full" />
            </div>
          ))}
        </div>
      ) : filteredCourses.length === 0 ? (
        <div className="p-12 text-center rounded-2xl border border-dashed border-slate-200 bg-slate-50/50 space-y-2">
          <Compass className="w-8 h-8 text-slate-400 mx-auto stroke-[1.5]" />
          <p className="text-sm font-semibold text-slate-700">No courses match your search</p>
          <p className="text-xs text-slate-400">Try adjusting your keywords</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filteredCourses.map((course) => {
            const isCompleted = course.enrollment?.is_completed;
            const progress = course.enrollment?.overall_progress || 0;

            return (
              <div
                key={course.id}
                className={`group relative bg-white rounded-2xl border border-slate-100 ${
                  isBanking ? 'hover:border-pink-300/80' : 'hover:border-orange-200'
                } shadow-xs hover:shadow-md transition-all duration-200 p-6 flex flex-col justify-between space-y-5`}
              >
                <div className="space-y-3">
                  {/* Top Metadata Badges */}
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 bg-slate-100 px-2.5 py-0.5 rounded-full">
                      {course.domain}
                    </span>
                    {isCompleted ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200/60">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        Completed
                      </span>
                    ) : progress > 0 ? (
                      <span className={`text-[11px] font-semibold ${
                        isBanking ? 'text-[#97144d] bg-pink-50 border-pink-200/60' : 'text-[#f05a28] bg-orange-50 border-orange-200/60'
                      } px-2.5 py-0.5 rounded-full border`}>
                        {progress}% done
                      </span>
                    ) : (
                      <span className="text-[11px] font-medium text-slate-400">
                        Not started
                      </span>
                    )}
                  </div>

                  {/* Course Title & Target */}
                  <div>
                    <h3 className={`text-base md:text-lg font-bold text-slate-900 ${
                      isBanking ? 'group-hover:text-[#97144d]' : 'group-hover:text-[#f05a28]'
                    } transition-colors`}>
                      {course.title}
                    </h3>
                    <p className="text-xs font-mono text-slate-500 mt-0.5">
                      Target: <span className="text-slate-700 font-semibold">{course.target_service}</span>
                    </p>
                  </div>

                  {/* Description */}
                  <p className="text-xs text-slate-600 leading-relaxed line-clamp-3">
                    {course.description}
                  </p>

                  {/* Tags */}
                  {course.tags && course.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {course.tags.map((tag) => (
                        <span
                          key={tag}
                          className="text-[10px] font-medium text-slate-500 bg-slate-50 border border-slate-200/60 px-2 py-0.5 rounded-md"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Card Footer: Metadata & Action CTA */}
                <div className="pt-4 border-t border-slate-100 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 text-slate-500 text-[11px]">
                    <span className="flex items-center gap-1" title="Estimated duration">
                      <Clock className="w-3.5 h-3.5" />
                      {course.estimated_duration}
                    </span>
                    <span className="flex items-center gap-1" title="Number of structured lessons">
                      <Layers className="w-3.5 h-3.5" />
                      {course.total_lessons} lessons
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {(progress > 0 || isCompleted) && onRestartCourse && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (window.confirm(`Restart "${course.title}" from Lesson 1? Progress will be reset.`)) {
                            onRestartCourse(course.id);
                          }
                        }}
                        className="flex items-center gap-1 px-2.5 py-2 rounded-xl text-xs font-semibold text-slate-500 hover:text-rose-600 hover:bg-rose-50 border border-slate-200 transition-colors cursor-pointer"
                        title="Restart course from beginning"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        <span>Restart</span>
                      </button>
                    )}
                    <button
                      onClick={() => onSelectCourse(course.id)}
                      className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-slate-900 ${
                        isBanking ? 'hover:bg-[#97144d]' : 'hover:bg-[#f05a28]'
                      } transition-colors cursor-pointer shadow-xs`}
                    >
                      {isCompleted ? (
                        <>
                          <RotateCcw className="w-3.5 h-3.5" />
                          Review
                        </>
                      ) : progress > 0 ? (
                        <>
                          <Play className="w-3.5 h-3.5 fill-white" />
                          Resume
                        </>
                      ) : (
                        <>
                          <Play className="w-3.5 h-3.5 fill-white" />
                          Start KT
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
