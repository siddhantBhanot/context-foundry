import { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import apiClient from '@/lib/api/client';
import { CourseCatalog } from './CourseCatalog';
import { CurriculumSidebar } from './CurriculumSidebar';
import { LessonViewer } from './LessonViewer';
import { LessonDoubtDrawer } from './LessonDoubtDrawer';
import { CourseCompletionModal } from './CourseCompletionModal';
import type { CourseDetail, CourseSummary, LessonDetail, LessonDoubt } from '@/types';

interface KnowledgeCafeViewProps {
  selectedModel: string;
  userRole?: 'developer' | 'banking_staff';
  onViewSource: (file: string, service?: string) => void;
  onExploreInChat: (service: string) => void;
}

export function KnowledgeCafeView({
  selectedModel,
  userRole,
  onViewSource,
  onExploreInChat,
}: KnowledgeCafeViewProps) {
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [isLoadingCatalog, setIsLoadingCatalog] = useState<boolean>(true);
  const [activeCourseId, setActiveCourseId] = useState<string | null>(null);
  const [activeCourse, setActiveCourse] = useState<CourseDetail | null>(null);
  const [activeLessonId, setActiveLessonId] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);
  const [activeLesson, setActiveLesson] = useState<LessonDetail | null>(null);
  const [isLoadingLesson, setIsLoadingLesson] = useState<boolean>(false);
  const [isDoubtDrawerOpen, setIsDoubtDrawerOpen] = useState<boolean>(false);
  const [isAskingDoubt, setIsAskingDoubt] = useState<boolean>(false);
  const [isCompletionModalOpen, setIsCompletionModalOpen] = useState<boolean>(false);

  // Load course catalog
  const loadCourses = async () => {
    setIsLoadingCatalog(true);
    try {
      const targetGroup = userRole === 'banking_staff' ? 'banking' : 'technical';
      const res = await apiClient.listCourses(targetGroup);
      setCourses(res);
    } catch (e) {
      console.error('Failed to load courses:', e);
    } finally {
      setIsLoadingCatalog(false);
    }
  };

  useEffect(() => {
    loadCourses();
  }, [userRole]);

  // Handle Course Selection & Enrollment
  const handleSelectCourse = async (courseId: string) => {
    try {
      setActiveCourseId(courseId);
      setIsLoadingLesson(true);

      // Enroll or resume
      const enrollRes = await apiClient.enrollInCourse(courseId);
      setActiveCourse(enrollRes.course);

      const targetLessonId =
        enrollRes.current_lesson?.id || enrollRes.course.lessons[0]?.id;

      if (targetLessonId) {
        await handleSelectLesson(targetLessonId, courseId);
      }
    } catch (e) {
      console.error('Error starting course:', e);
      setIsLoadingLesson(false);
    }
  };

  // Handle Course Restart
  const handleRestartCourse = async (courseId: string) => {
    try {
      setActiveCourseId(courseId);
      setIsLoadingLesson(true);

      const restartRes = await apiClient.restartCourse(courseId);
      setActiveCourse(restartRes.course);
      await loadCourses();

      const targetLessonId =
        restartRes.current_lesson?.id || restartRes.course.lessons[0]?.id;

      if (targetLessonId) {
        await handleSelectLesson(targetLessonId, courseId);
      }
    } catch (e) {
      console.error('Error restarting course:', e);
      setIsLoadingLesson(false);
    }
  };

  // Handle Lesson Switching with Real-Time Streaming
  const handleSelectLesson = async (lessonId: string, overrideCourseId?: string) => {
    const courseId = overrideCourseId || activeCourseId;
    if (!courseId) return;

    setActiveLessonId(lessonId);
    setIsLoadingLesson(true);

    try {
      await apiClient.getLessonContentStream(
        courseId,
        lessonId,
        selectedModel,
        {
          onMetadata: (meta) => {
            setActiveLesson({
              course_id: meta.course_id,
              lesson_id: meta.lesson_id,
              lesson_index: meta.lesson_index,
              title: meta.title,
              summary: meta.summary,
              content: '',
              takeaways: meta.takeaways || [],
              sources: meta.sources || [],
              knowledge_check: meta.knowledge_check,
              knowledge_checks: meta.knowledge_checks || (meta.knowledge_check ? [meta.knowledge_check] : []),
              doubts: meta.doubts || [],
              is_completed: meta.is_completed,
              model: meta.model,
            });
            if (meta.is_cached) {
              setIsLoadingLesson(false);
            }
          },
          onChunk: (chunk) => {
            setIsLoadingLesson(false);
            setActiveLesson((prev) => (prev ? { ...prev, content: prev.content + chunk } : prev));
          },
          onDone: (done) => {
            setIsLoadingLesson(false);
            setActiveLesson((prev) =>
              prev
                ? {
                    ...prev,
                    content: done.clean_content || prev.content,
                    takeaways: done.takeaways || prev.takeaways,
                  }
                : prev
            );
          },
          onError: (err) => {
            setIsLoadingLesson(false);
            console.error('Lesson stream error:', err);
          },
        }
      );
    } catch (e) {
      console.error('Error fetching lesson stream:', e);
      setIsLoadingLesson(false);
    }
  };

  // Handle Complete & Next Lesson Flow
  const handleContinueLesson = async () => {
    if (!activeCourseId || !activeLessonId) return;

    try {
      const compRes = await apiClient.completeLesson(activeCourseId, activeLessonId);

      // Update local course details
      if (activeCourse) {
        const updatedLessons = activeCourse.lessons.map((l) => {
          if (l.id === activeLessonId) {
            return { ...l, status: 'completed' as const };
          }
          if (compRes.next_lesson && l.id === compRes.next_lesson.id) {
            return { ...l, status: 'current' as const };
          }
          return l;
        });

        setActiveCourse({
          ...activeCourse,
          enrollment: compRes.enrollment,
          lessons: updatedLessons,
        });
      }

      // Check if course is complete
      if (compRes.is_course_completed) {
        setIsCompletionModalOpen(true);
      } else if (compRes.next_lesson) {
        handleSelectLesson(compRes.next_lesson.id);
      }
    } catch (e) {
      console.error('Error completing lesson:', e);
    }
  };

  // Handle In-Lesson Doubt with Real-Time Streaming
  const handleAskDoubt = async (question: string) => {
    if (!activeCourseId || !activeLessonId) return;
    setIsAskingDoubt(true);
    const tempDoubtId = `doubt-${Date.now()}`;
    const pendingDoubt: LessonDoubt = {
      id: tempDoubtId,
      user_id: '',
      course_id: activeCourseId,
      lesson_id: activeLessonId,
      question: question,
      answer: '',
      sources: [],
      created_at: new Date().toISOString(),
    };

    if (activeLesson) {
      setActiveLesson({
        ...activeLesson,
        doubts: [...activeLesson.doubts, pendingDoubt],
      });
    }

    let currentDoubtId = tempDoubtId;

    try {
      await apiClient.askLessonDoubtStream(
        activeCourseId,
        activeLessonId,
        question,
        selectedModel,
        {
          onMetadata: (meta) => {
            if (meta.doubt_id) {
              currentDoubtId = meta.doubt_id;
            }
            setActiveLesson((prev) => {
              if (!prev) return prev;
              return {
                ...prev,
                doubts: prev.doubts.map((d) =>
                  d.id === tempDoubtId
                    ? { ...d, id: meta.doubt_id || d.id, sources: meta.sources || [] }
                    : d
                ),
              };
            });
          },
          onChunk: (chunk) => {
            setActiveLesson((prev) => {
              if (!prev) return prev;
              return {
                ...prev,
                doubts: prev.doubts.map((d) =>
                  d.id === currentDoubtId || d.id === tempDoubtId || (d.id.startsWith('doubt-') && !d.answer)
                    ? { ...d, answer: (d.answer || '') + chunk }
                    : d
                ),
              };
            });
          },
          onDone: (done) => {
            setIsAskingDoubt(false);
            setActiveLesson((prev) => {
              if (!prev) return prev;
              return {
                ...prev,
                doubts: prev.doubts.map((d) =>
                  d.id === currentDoubtId || d.id === tempDoubtId || d.id === done.doubt.id
                    ? done.doubt
                    : d
                ),
              };
            });
          },
          onError: (err) => {
            setIsAskingDoubt(false);
            console.error('Doubt stream error:', err);
          },
        }
      );
    } catch (e) {
      console.error('Error asking doubt stream:', e);
      setIsAskingDoubt(false);
    }
  };


  // Handle Knowledge Check Submission
  const handleSubmitCheck = async (
    selectedOptionIndex?: number,
    questionIndex: number = 0,
    answers?: number[]
  ) => {
    if (!activeCourseId || !activeLessonId) {
      throw new Error('No active lesson');
    }
    return apiClient.submitKnowledgeCheck(
      activeCourseId,
      activeLessonId,
      selectedOptionIndex,
      questionIndex,
      answers
    );
  };

  // Return to Catalog
  const handleBackToCatalog = () => {
    setActiveCourseId(null);
    setActiveCourse(null);
    setActiveLessonId(null);
    setActiveLesson(null);
    loadCourses();
  };

  // If viewing catalog
  if (!activeCourseId || !activeCourse) {
    return (
      <CourseCatalog
        courses={courses}
        isLoading={isLoadingCatalog}
        userRole={userRole}
        onSelectCourse={handleSelectCourse}
        onRestartCourse={handleRestartCourse}
      />
    );
  }

  // Current lesson index check for last lesson
  const currentLessonIndex = activeCourse.lessons.findIndex((l) => l.id === activeLessonId);
  const isLastLesson = currentLessonIndex === activeCourse.lessons.length - 1;

  return (
    <div className="flex-1 flex overflow-hidden h-full relative">
      {/* 10-Lesson Creator Curriculum Sidebar */}
      <div
        className={`relative transition-[width,margin] duration-300 ease-in-out shrink-0 h-full flex ${
          isSidebarOpen ? 'w-80 md:w-88' : 'w-0'
        }`}
      >
        <div className="w-80 md:w-88 h-full overflow-hidden">
          <CurriculumSidebar
            course={activeCourse}
            activeLessonId={activeLessonId || ''}
            onSelectLesson={handleSelectLesson}
            onBackToCatalog={handleBackToCatalog}
          />
        </div>

        {/* Boundary Collapse Button (when expanded) */}
        {isSidebarOpen && (
          <button
            type="button"
            onClick={() => setIsSidebarOpen(false)}
            className="absolute -right-3.5 top-7 sm:top-8 z-20 w-7 h-7 rounded-full bg-white border border-slate-200 text-slate-500 hover:text-[#f05a28] hover:border-orange-300 hover:bg-orange-50 shadow-xs flex items-center justify-center transition-all hover:scale-105 cursor-pointer"
            title="Collapse curriculum sidebar"
            aria-label="Collapse curriculum sidebar"
          >
            <ChevronLeft className="w-3.5 h-3.5 stroke-[2.5]" />
          </button>
        )}
      </div>

      {/* Boundary Expand Button (when collapsed) */}
      {!isSidebarOpen && (
        <button
          type="button"
          onClick={() => setIsSidebarOpen(true)}
          className="absolute left-0 top-7 sm:top-8 z-20 flex items-center gap-1.5 px-3 py-1.5 rounded-r-xl bg-white border-y border-r border-slate-200 shadow-sm text-xs font-semibold text-slate-600 hover:text-[#f05a28] hover:bg-orange-50/80 hover:border-orange-300 transition-all cursor-pointer group animate-in fade-in slide-in-from-left duration-200"
          title="Expand curriculum sidebar"
          aria-label="Expand curriculum sidebar"
        >
          <ChevronRight className="w-4 h-4 text-[#f05a28] stroke-[2.5] group-hover:translate-x-0.5 transition-transform" />
          <span className="text-[11px] font-semibold text-slate-700 group-hover:text-[#f05a28]">
            Curriculum
          </span>
        </button>
      )}

      {/* Main Lesson Reading Panel */}
      {activeLesson ? (
        <LessonViewer
          lesson={activeLesson}
          isLoading={isLoadingLesson}
          onContinue={handleContinueLesson}
          onOpenDoubtDrawer={() => setIsDoubtDrawerOpen(true)}
          onViewSource={onViewSource}
          onSubmitCheck={handleSubmitCheck}
          isLastLesson={isLastLesson}
          isSidebarCollapsed={!isSidebarOpen}
          onRestartCourse={() => activeCourseId && handleRestartCourse(activeCourseId)}
        />
      ) : (
        <div className="flex-1 flex items-center justify-center text-xs text-slate-400">
          Loading lesson...
        </div>
      )}

      {/* Interactive Doubt Clearing Drawer */}
      <LessonDoubtDrawer
        isOpen={isDoubtDrawerOpen}
        onClose={() => setIsDoubtDrawerOpen(false)}
        lessonTitle={activeLesson?.title || ''}
        courseId={activeCourseId || ''}
        doubts={activeLesson?.doubts || []}
        onAskDoubt={handleAskDoubt}
        isAsking={isAskingDoubt}
      />

      {/* Completion Modal */}
      <CourseCompletionModal
        isOpen={isCompletionModalOpen}
        onClose={() => setIsCompletionModalOpen(false)}
        course={activeCourse}
        onExploreInChat={onExploreInChat}
      />
    </div>
  );
}
