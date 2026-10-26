import { useEffect, useState } from 'react';
import {
  ArrowRight,
  CheckCircle2,
  Cpu,
  FileText,
  HelpCircle,
  Lightbulb,
  Loader2,
  MessageSquare,
  RotateCcw,
  Sparkles,
  XCircle,
} from 'lucide-react';
import { MarkdownRenderer } from '@/components/chat/MarkdownRenderer';
import type { KnowledgeCheck, KnowledgeCheckResult, LessonDetail } from '@/types';

interface LessonViewerProps {
  lesson: LessonDetail;
  isLoading: boolean;
  onContinue: () => void;
  onOpenDoubtDrawer: () => void;
  onViewSource: (file: string, service?: string) => void;
  onSubmitCheck: (
    selectedOptionIndex?: number,
    questionIndex?: number,
    answers?: number[]
  ) => Promise<KnowledgeCheckResult>;
  isLastLesson: boolean;
  isSidebarCollapsed?: boolean;
  onRestartCourse?: () => void;
}

export function LessonViewer({
  lesson,
  isLoading,
  onContinue,
  onOpenDoubtDrawer,
  onViewSource,
  onSubmitCheck,
  isLastLesson,
  isSidebarCollapsed = false,
  onRestartCourse,
}: LessonViewerProps) {
  // Knowledge Check State - supports multi-question quiz
  const questions: KnowledgeCheck[] =
    lesson.knowledge_checks && lesson.knowledge_checks.length > 0
      ? lesson.knowledge_checks
      : lesson.knowledge_check
      ? [lesson.knowledge_check]
      : [];

  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, number>>({});
  const [isSubmittingCheck, setIsSubmittingCheck] = useState(false);
  const [checkResult, setCheckResult] = useState<KnowledgeCheckResult | null>(null);

  // Reset quiz state when switching lessons
  useEffect(() => {
    setSelectedAnswers({});
    setCheckResult(null);
  }, [lesson.lesson_id]);

  const handleSelectOption = (qIdx: number, optIdx: number) => {
    if (checkResult) return;
    setSelectedAnswers((prev) => ({
      ...prev,
      [qIdx]: optIdx,
    }));
  };

  const answeredCount = Object.keys(selectedAnswers).length;

  const handleCheckSubmit = async () => {
    if (answeredCount === 0 || isSubmittingCheck) return;
    setIsSubmittingCheck(true);
    try {
      if (questions.length > 1) {
        const answersArray = questions.map((_, idx) =>
          selectedAnswers[idx] !== undefined ? selectedAnswers[idx] : 0
        );
        const res = await onSubmitCheck(undefined, 0, answersArray);
        setCheckResult(res);
      } else {
        const sel = selectedAnswers[0] ?? 0;
        const res = await onSubmitCheck(sel, 0, undefined);
        setCheckResult(res);
      }
    } catch (e) {
      console.error('Error submitting knowledge check:', e);
    } finally {
      setIsSubmittingCheck(false);
    }
  };

  const handleRetakeQuiz = () => {
    setSelectedAnswers({});
    setCheckResult(null);
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-12 space-y-4">
        <div className="relative">
          <Loader2 className="w-8 h-8 text-[#f05a28] animate-spin" />
          <Sparkles className="w-3.5 h-3.5 text-amber-500 absolute -top-1 -right-1 animate-pulse" />
        </div>
        <div className="text-center space-y-1">
          <p className="text-sm font-semibold text-slate-800">Synthesizing Guided Lesson...</p>
          <p className="text-xs text-slate-500">
            Grounding concepts in dedicated course context files
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`flex-1 overflow-y-auto pt-8 md:pt-10 pb-12 md:pb-16 ${
        isSidebarCollapsed
          ? 'px-8 sm:px-14 md:px-16 max-w-5xl xl:max-w-6xl'
          : 'px-6 md:px-12 max-w-4xl'
      } mx-auto w-full space-y-8 animate-in fade-in duration-300`}
    >
      {/* Lesson Header */}
      <div className="space-y-2 pb-6 border-b border-slate-100">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#f05a28] bg-orange-50 px-2.5 py-0.5 rounded-full border border-orange-200/60">
              Lesson {lesson.lesson_index + 1}
            </span>
            {lesson.is_completed && (
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200/60">
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                Completed
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {isLoading && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-orange-50 text-orange-700 border border-orange-200 animate-pulse">
                <span className="w-1.5 h-1.5 rounded-full bg-[#f05a28]" />
                Streaming Live
              </span>
            )}
            {lesson.model && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-600 border border-slate-200/80">
                <Cpu className="w-3 h-3 text-slate-400" />
                {lesson.model}
              </span>
            )}
            {onRestartCourse && (
              <button
                type="button"
                onClick={() => {
                  if (window.confirm('Restart this entire course from Lesson 1? Progress will be reset.')) {
                    onRestartCourse();
                  }
                }}
                className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium text-slate-500 hover:text-rose-600 bg-slate-100 hover:bg-rose-50 border border-slate-200 transition-colors cursor-pointer"
                title="Restart course from Lesson 1"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Restart Course</span>
              </button>
            )}
          </div>
        </div>

        <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900">
          {lesson.title}
        </h1>
        {lesson.summary && (
          <p className="text-sm text-slate-600 leading-relaxed">{lesson.summary}</p>
        )}
      </div>

      {/* Main Markdown Lesson Content */}
      <div className="bg-white text-slate-900 leading-relaxed font-sans text-sm md:text-base relative">
        <MarkdownRenderer content={lesson.content} />
        {isLoading && lesson.content && (
          <span className="inline-block w-2 h-4 ml-1 bg-[#f05a28] animate-pulse align-middle" />
        )}
      </div>


      {/* Key Takeaways Card */}
      {lesson.takeaways && lesson.takeaways.length > 0 && (
        <div className="bg-gradient-to-br from-amber-500/10 via-orange-500/5 to-transparent border border-amber-200/80 rounded-2xl p-6 shadow-xs space-y-3">
          <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
            <Lightbulb className="w-4 h-4 text-[#f05a28]" />
            Key Takeaways
          </div>
          <ul className="space-y-2 text-xs md:text-sm text-slate-700">
            {lesson.takeaways.map((takeaway, idx) => (
              <li key={idx} className="flex items-start gap-2.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#f05a28] mt-2 shrink-0" />
                <span>{takeaway}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Grounded Source Context References */}
      {lesson.sources && lesson.sources.length > 0 && (
        <div className="space-y-2 pt-2">
          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-600 uppercase tracking-wider">
            <FileText className="w-3.5 h-3.5 text-slate-400" />
            Dedicated Course Context Files ({lesson.sources.length})
          </div>
          <div className="flex flex-wrap gap-2">
            {lesson.sources.map((src, idx) => (
              <button
                key={idx}
                onClick={() => onViewSource(src.file, lesson.course_id)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-50 hover:bg-orange-50 border border-slate-200/80 hover:border-orange-300 text-xs font-medium text-slate-700 hover:text-[#f05a28] transition-colors cursor-pointer"
                title="Click to view full course source document"
              >
                <FileText className="w-3 h-3 text-slate-400" />
                <span>{src.file}</span>
                <span className="text-[10px] text-slate-400">· View Source</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Interactive Knowledge Check */}
      {questions.length > 0 && (
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 sm:p-7 shadow-xs space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
            <div>
              <div className="flex items-center gap-2 text-slate-900 font-bold text-base">
                <HelpCircle className="w-5 h-5 text-[#f05a28]" />
                <span>Knowledge Check</span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-orange-50 text-[#f05a28] border border-orange-200/60">
                  {questions.length} Questions
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Test your understanding of the key concepts covered in this lesson.
              </p>
            </div>

            {checkResult && (
              <div className="flex items-center gap-2">
                <span
                  className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${
                    checkResult.is_correct
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : 'bg-amber-50 text-amber-800 border-amber-200'
                  }`}
                >
                  {checkResult.is_correct ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  ) : (
                    <Lightbulb className="w-3.5 h-3.5 text-amber-600" />
                  )}
                  Score: {checkResult.score ?? (checkResult.is_correct ? questions.length : 0)} / {questions.length} (
                  {Math.round(
                    ((checkResult.score ?? (checkResult.is_correct ? questions.length : 0)) /
                      questions.length) *
                      100
                  )}
                  %)
                </span>
                <button
                  onClick={handleRetakeQuiz}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50 text-xs font-medium text-slate-600 transition-colors cursor-pointer"
                  title="Retake this quiz"
                >
                  <RotateCcw className="w-3 h-3 text-slate-500" />
                  Retake
                </button>
              </div>
            )}
          </div>

          {/* List of questions */}
          <div className="space-y-6">
            {questions.map((q, qIdx) => {
              const qResult =
                checkResult?.results?.find((r) => r.question_index === qIdx) ||
                (questions.length === 1 && checkResult
                  ? {
                      is_correct: checkResult.is_correct,
                      correct_option_index: checkResult.correct_option_index ?? 0,
                      explanation: checkResult.explanation ?? '',
                    }
                  : null);

              return (
                <div
                  key={qIdx}
                  className="space-y-3 pb-6 border-b border-slate-100 last:border-b-0 last:pb-0"
                >
                  <div className="flex items-start gap-2.5">
                    <span className="shrink-0 flex items-center justify-center w-6 h-6 rounded-lg bg-slate-100 text-[11px] font-bold text-slate-700 mt-0.5">
                      Q{qIdx + 1}
                    </span>
                    <div className="flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-xs md:text-sm font-semibold text-slate-900 leading-snug">
                          {q.question}
                        </p>
                        {qResult && (
                          <div className="shrink-0">
                            {qResult.is_correct ? (
                              <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                                <CheckCircle2 className="w-3 h-3" /> Correct
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-[11px] font-bold text-rose-600 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
                                <XCircle className="w-3 h-3" /> Incorrect
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* 4 Options */}
                  <div className="space-y-2 pl-8">
                    {q.options.map((opt, optIdx) => {
                      const isSelected = selectedAnswers[qIdx] === optIdx;
                      const isCorrectAnswer =
                        qResult && qResult.correct_option_index === optIdx;
                      const isWrongSelected =
                        qResult && !qResult.is_correct && isSelected;

                      return (
                        <label
                          key={optIdx}
                          className={`flex items-start gap-3 p-3 rounded-xl border transition-all ${
                            isCorrectAnswer
                              ? 'bg-emerald-50/90 border-emerald-300 text-emerald-950 font-medium'
                              : isWrongSelected
                              ? 'bg-rose-50/90 border-rose-300 text-rose-950'
                              : isSelected
                              ? 'bg-orange-50/60 border-[#f05a28] text-slate-900 shadow-xs'
                              : 'bg-slate-50/60 hover:bg-white border-slate-200/80 text-slate-700 hover:border-slate-300'
                          } ${!checkResult ? 'cursor-pointer' : 'cursor-default'}`}
                        >
                          <input
                            type="radio"
                            name={`knowledge_check_${qIdx}`}
                            checked={isSelected}
                            onChange={() => handleSelectOption(qIdx, optIdx)}
                            disabled={Boolean(checkResult)}
                            className="mt-1 accent-[#f05a28] cursor-pointer"
                          />
                          <span className="text-xs md:text-sm leading-relaxed">{opt}</span>
                        </label>
                      );
                    })}
                  </div>

                  {/* Explanation card if evaluated */}
                  {qResult && (
                    <div
                      className={`ml-8 p-3.5 rounded-xl text-xs space-y-1 mt-2.5 ${
                        qResult.is_correct
                          ? 'bg-emerald-50/70 border border-emerald-200/80 text-emerald-950'
                          : 'bg-rose-50/70 border border-rose-200/80 text-rose-950'
                      }`}
                    >
                      <div className="flex items-center gap-1.5 font-bold">
                        {qResult.is_correct ? (
                          <>
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                            <span>Explanation</span>
                          </>
                        ) : (
                          <>
                            <XCircle className="w-3.5 h-3.5 text-rose-600" />
                            <span>Explanation</span>
                          </>
                        )}
                      </div>
                      <p className="text-slate-700 leading-relaxed font-normal">
                        {qResult.explanation || q.explanation}
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Quiz Action Bar */}
          {!checkResult ? (
            <div className="flex items-center justify-between pt-2">
              <span className="text-xs text-slate-500 font-medium">
                {answeredCount} of {questions.length} answered
              </span>
              <button
                onClick={handleCheckSubmit}
                disabled={answeredCount === 0 || isSubmittingCheck}
                className="px-5 py-2.5 rounded-xl text-xs font-semibold text-white bg-slate-900 hover:bg-[#f05a28] disabled:opacity-40 disabled:hover:bg-slate-900 transition-all cursor-pointer shadow-xs flex items-center gap-2"
              >
                {isSubmittingCheck ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Grading Quiz...</span>
                  </>
                ) : (
                  <span>
                    Submit Answers ({answeredCount}/{questions.length})
                  </span>
                )}
              </button>
            </div>
          ) : (
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div
                  className={`p-2 rounded-xl shrink-0 ${
                    checkResult.is_correct
                      ? 'bg-emerald-100 text-emerald-700'
                      : 'bg-amber-100 text-amber-700'
                  }`}
                >
                  {checkResult.is_correct ? (
                    <CheckCircle2 className="w-5 h-5" />
                  ) : (
                    <Lightbulb className="w-5 h-5" />
                  )}
                </div>
                <div>
                  <p className="text-xs font-bold text-slate-800">
                    Quiz Completed · Score:{' '}
                    {checkResult.score ?? (checkResult.is_correct ? questions.length : 0)} /{' '}
                    {questions.length} (
                    {Math.round(
                      ((checkResult.score ?? (checkResult.is_correct ? questions.length : 0)) /
                        questions.length) *
                        100
                    )}
                    %)
                  </p>
                  <p className="text-[11px] text-slate-500">
                    {checkResult.is_correct
                      ? 'Outstanding work! You answered all questions correctly.'
                      : 'Review the explanations above to solidify your understanding.'}
                  </p>
                </div>
              </div>
              <button
                onClick={handleRetakeQuiz}
                className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 hover:border-slate-300 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 transition-colors cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
                Retake Quiz
              </button>
            </div>
          )}
        </div>
      )}

      {/* Bottom Sticky-style Action Bar */}
      <div className="pt-6 pb-6 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Ask a Question Trigger */}
        <button
          onClick={onOpenDoubtDrawer}
          className="w-full sm:w-auto flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 transition-colors cursor-pointer shadow-xs"
        >
          <MessageSquare className="w-4 h-4 text-[#f05a28]" />
          Ask a Question
          {lesson.doubts && lesson.doubts.length > 0 && (
            <span className="px-1.5 py-0.5 rounded-full bg-slate-100 text-[10px] text-slate-600">
              {lesson.doubts.length}
            </span>
          )}
        </button>

        {/* Continue / Next Lesson CTA */}
        <button
          onClick={onContinue}
          className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-[#f05a28] hover:bg-[#d94819] text-white text-xs md:text-sm font-semibold shadow-xs transition-transform active:scale-95 cursor-pointer"
        >
          <span>{isLastLesson ? 'Complete Course 🎉' : 'Continue →'}</span>
          {!isLastLesson && <ArrowRight className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );
}
