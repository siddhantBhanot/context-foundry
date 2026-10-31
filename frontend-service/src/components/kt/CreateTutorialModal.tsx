import React, { useState } from 'react';
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  Clock,
  HelpCircle,
  Layers,
  Loader2,
  Plus,
  Sparkles,
  Trash2,
  X,
} from 'lucide-react';
import apiClient from '@/lib/api/client';
import type {
  CreateCoursePayload,
  CreateCourseResult,
  CreateLessonPayload,
  Microservice,
  QuizQuestionPayload,
} from '@/types';

interface CreateTutorialModalProps {
  isOpen: boolean;
  onClose: () => void;
  services: Microservice[];
  defaultService?: string;
  onSuccess: (course: CreateCourseResult) => void;
}

export function CreateTutorialModal({
  isOpen,
  onClose,
  services,
  defaultService,
  onSuccess,
}: CreateTutorialModalProps) {
  const [title, setTitle] = useState('');
  const [targetService, setTargetService] = useState(
    defaultService || (services.length > 0 ? services[0].id : '')
  );
  const [description, setDescription] = useState('');
  const [difficulty, setDifficulty] = useState('Intermediate');
  const [estimatedDuration, setEstimatedDuration] = useState('45 mins');
  const [lessons, setLessons] = useState<CreateLessonPayload[]>([
    {
      title: 'Architecture Overview & Domain Models',
      summary: 'High-level architectural blueprint and core domain structures.',
      content:
        '## System Architecture\n\nThis lesson introduces the core components and domain model entities.\n\n### Key Principles\n- Clean domain separation\n- Idempotent request handling\n- Resilient persistence layer',
      quiz_questions: [
        {
          question: 'What is the primary role of this microservice?',
          options: [
            'Serving edge routing only',
            'Executing domain business logic and state transitions',
            'Ephemeral client caching',
            'Static asset delivery',
          ],
          correct_option_index: 1,
          explanation:
            'The service encapsulates core business workflows and state transitions with strong typing.',
        },
      ],
    },
  ]);

  const [activeLessonIdx, setActiveLessonIdx] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleAddLesson = () => {
    const nextNum = lessons.length + 1;
    const newLesson: CreateLessonPayload = {
      title: `Lesson ${nextNum}: Core Workflow Execution`,
      summary: 'Deep-dive into verified service call paths and logic.',
      content: `## Workflow Deep Dive\n\nExplain specific call flows and implementation details here.\n\n\`\`\`kotlin\n// Example logic\nfun executeWorkflow(req: Request): Response {\n    return Response.success()\n}\n\`\`\``,
      quiz_questions: [],
    };
    setLessons([...lessons, newLesson]);
    setActiveLessonIdx(lessons.length);
  };

  const handleRemoveLesson = (index: number) => {
    if (lessons.length <= 1) {
      setError('A tutorial must contain at least one lesson.');
      return;
    }
    const updated = lessons.filter((_, i) => i !== index);
    setLessons(updated);
    if (activeLessonIdx >= updated.length) {
      setActiveLessonIdx(updated.length - 1);
    }
  };

  const handleUpdateLesson = (field: keyof CreateLessonPayload, value: any) => {
    setLessons((prev) => {
      const copy = [...prev];
      copy[activeLessonIdx] = { ...copy[activeLessonIdx], [field]: value };
      return copy;
    });
  };

  const handleAddQuizQuestion = () => {
    const currentQuestions = lessons[activeLessonIdx]?.quiz_questions || [];
    const newQuestion: QuizQuestionPayload = {
      question: '',
      options: ['', '', '', ''],
      correct_option_index: 0,
      explanation: '',
    };
    handleUpdateLesson('quiz_questions', [...currentQuestions, newQuestion]);
  };

  const handleUpdateQuizQuestion = (qIdx: number, field: keyof QuizQuestionPayload, value: any) => {
    const currentQuestions = [...(lessons[activeLessonIdx]?.quiz_questions || [])];
    currentQuestions[qIdx] = { ...currentQuestions[qIdx], [field]: value };
    handleUpdateLesson('quiz_questions', currentQuestions);
  };

  const handleUpdateOption = (qIdx: number, optIdx: number, val: string) => {
    const currentQuestions = [...(lessons[activeLessonIdx]?.quiz_questions || [])];
    const options = [...currentQuestions[qIdx].options];
    options[optIdx] = val;
    currentQuestions[qIdx] = { ...currentQuestions[qIdx], options };
    handleUpdateLesson('quiz_questions', currentQuestions);
  };

  const handleRemoveQuizQuestion = (qIdx: number) => {
    const currentQuestions = (lessons[activeLessonIdx]?.quiz_questions || []).filter(
      (_, i) => i !== qIdx
    );
    handleUpdateLesson('quiz_questions', currentQuestions);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!title.trim()) {
      setError('Please provide a tutorial title.');
      return;
    }
    if (!targetService) {
      setError('Please select or specify a target microservice.');
      return;
    }
    if (lessons.length === 0) {
      setError('Please add at least one lesson.');
      return;
    }

    for (let i = 0; i < lessons.length; i++) {
      const l = lessons[i];
      if (!l.title.trim()) {
        setError(`Lesson ${i + 1} requires a title.`);
        return;
      }
      if (l.quiz_questions && l.quiz_questions.length > 0) {
        for (let q = 0; q < l.quiz_questions.length; q++) {
          const quest = l.quiz_questions[q];
          if (!quest.question.trim()) {
            setError(`Question ${q + 1} in Lesson "${l.title}" is missing question text.`);
            return;
          }
          if (quest.options.some((opt) => !opt.trim())) {
            setError(
              `All 4 options must be completed for question ${q + 1} in Lesson "${l.title}".`
            );
            return;
          }
        }
      }
    }

    setIsSubmitting(true);
    try {
      const payload: CreateCoursePayload = {
        title: title.trim(),
        description: description.trim() || `Comprehensive developer curriculum for ${targetService}.`,
        target_service: targetService,
        difficulty,
        estimated_duration: estimatedDuration,
        lessons: lessons.map((l) => ({
          title: l.title.trim(),
          summary: l.summary.trim(),
          content: l.content?.trim() || '',
          quiz_questions: l.quiz_questions,
        })),
      };

      const result = await apiClient.createCourse(payload);
      onSuccess(result);
      onClose();
    } catch (err: any) {
      console.error('Failed to create tutorial:', err);
      setError(err?.message || 'Failed to create and index course tutorial.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const activeLesson = lessons[activeLessonIdx];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl border border-slate-200 shadow-2xl w-full max-w-4xl max-h-[92vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/70 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-orange-100/80 text-[#f05a28] flex items-center justify-center shadow-xs">
              <BookOpen className="w-5 h-5 stroke-[2.2]" />
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-bold text-slate-900 flex items-center gap-2">
                Create Knowledge Cafe Tutorial
                <span className="text-[10px] font-semibold uppercase tracking-wider text-orange-600 bg-orange-100/70 px-2 py-0.5 rounded-full">
                  Authoring
                </span>
              </h2>
              <p className="text-xs text-slate-500">
                Author and index a custom onboarding curriculum grounded in service architecture
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mx-6 mt-4 p-3 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-2.5 text-xs text-rose-700">
            <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Form Body (Scrollable) */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Metadata Section */}
          <div className="bg-slate-50/70 border border-slate-200/80 rounded-2xl p-4.5 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-[#f05a28]" />
              Tutorial Metadata
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1 sm:col-span-2">
                <label className="text-xs font-semibold text-slate-700">
                  Course Title <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Account Settlement Service: Core Architecture & Flow"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-xl border border-slate-200 bg-white focus:outline-none focus:border-[#f05a28] shadow-xs"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700">
                  Target Microservice <span className="text-rose-500">*</span>
                </label>
                <select
                  value={targetService}
                  onChange={(e) => setTargetService(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-xl border border-slate-200 bg-white focus:outline-none focus:border-[#f05a28] shadow-xs cursor-pointer font-medium text-slate-700"
                >
                  {services.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.id})
                    </option>
                  ))}
                  {!services.some((s) => s.id === targetService) && targetService && (
                    <option value={targetService}>{targetService}</option>
                  )}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Difficulty</label>
                  <select
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value)}
                    className="w-full text-xs px-3 py-2 rounded-xl border border-slate-200 bg-white focus:outline-none focus:border-[#f05a28] shadow-xs cursor-pointer"
                  >
                    <option value="Beginner">Beginner</option>
                    <option value="Intermediate">Intermediate</option>
                    <option value="Advanced">Advanced</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700">Duration</label>
                  <input
                    type="text"
                    value={estimatedDuration}
                    onChange={(e) => setEstimatedDuration(e.target.value)}
                    placeholder="e.g. 45 mins"
                    className="w-full text-xs px-3 py-2 rounded-xl border border-slate-200 bg-white focus:outline-none focus:border-[#f05a28] shadow-xs"
                  />
                </div>
              </div>

              <div className="space-y-1 sm:col-span-2">
                <label className="text-xs font-semibold text-slate-700">Description</label>
                <textarea
                  rows={2}
                  placeholder="Summarize the core takeaways, target audience, and architecture covered in this tutorial..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-xl border border-slate-200 bg-white focus:outline-none focus:border-[#f05a28] shadow-xs resize-none"
                />
              </div>
            </div>
          </div>

          {/* Lessons Master-Detail Builder */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-[#f05a28]" />
                Curriculum Lessons ({lessons.length})
              </h3>
              <button
                type="button"
                onClick={handleAddLesson}
                className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-orange-50 text-[#f05a28] border border-orange-200/80 text-xs font-semibold hover:bg-orange-100 transition-colors cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Lesson
              </button>
            </div>

            {/* Lesson Tab Selector */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1.5 scrollbar-thin">
              {lessons.map((lesson, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setActiveLessonIdx(idx)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold shrink-0 transition-all flex items-center gap-2 cursor-pointer ${
                    activeLessonIdx === idx
                      ? 'bg-slate-900 text-white shadow-xs'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  <span>{idx + 1}. {lesson.title.slice(0, 18) || 'Untitled'}...</span>
                  {lessons.length > 1 && (
                    <span
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveLesson(idx);
                      }}
                      className="hover:text-rose-400 p-0.5"
                      title="Delete lesson"
                    >
                      <Trash2 className="w-3 h-3" />
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Active Lesson Editor Panel */}
            {activeLesson && (
              <div className="bg-white border border-slate-200 rounded-2xl p-4.5 space-y-4 shadow-xs">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1 sm:col-span-2">
                    <label className="text-xs font-semibold text-slate-700">
                      Lesson Title <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={activeLesson.title}
                      onChange={(e) => handleUpdateLesson('title', e.target.value)}
                      placeholder="e.g. Ingestion Pipeline & Chunking Engine"
                      className="w-full text-xs px-3 py-2 rounded-xl border border-slate-200 bg-white focus:outline-none focus:border-[#f05a28] shadow-xs"
                    />
                  </div>

                  <div className="space-y-1 sm:col-span-2">
                    <label className="text-xs font-semibold text-slate-700">Lesson Summary</label>
                    <input
                      type="text"
                      value={activeLesson.summary}
                      onChange={(e) => handleUpdateLesson('summary', e.target.value)}
                      placeholder="Brief one-line recap shown in curriculum navigation..."
                      className="w-full text-xs px-3 py-2 rounded-xl border border-slate-200 bg-white focus:outline-none focus:border-[#f05a28] shadow-xs"
                    />
                  </div>

                  <div className="space-y-1 sm:col-span-2">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-semibold text-slate-700">
                        Lesson Content (Markdown & Code)
                      </label>
                      <span className="text-[10px] text-slate-400">
                        Supports markdown, Kotlin snippets, and Mermaid charts
                      </span>
                    </div>
                    <textarea
                      rows={6}
                      value={activeLesson.content}
                      onChange={(e) => handleUpdateLesson('content', e.target.value)}
                      placeholder="Write your tutorial markdown here with headers, code blocks, bullet points..."
                      className="w-full font-mono text-xs px-3 py-2 rounded-xl border border-slate-200 bg-slate-50/50 focus:bg-white focus:outline-none focus:border-[#f05a28] shadow-xs"
                    />
                  </div>
                </div>

                {/* Knowledge Check Questions for this lesson */}
                <div className="border-t border-slate-100 pt-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                      <HelpCircle className="w-3.5 h-3.5 text-orange-500" />
                      Knowledge Check Quiz ({(activeLesson.quiz_questions || []).length})
                    </label>
                    <button
                      type="button"
                      onClick={handleAddQuizQuestion}
                      className="text-xs font-semibold text-[#f05a28] hover:text-[#d94b1c] flex items-center gap-1 cursor-pointer"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Add Question
                    </button>
                  </div>

                  {(!activeLesson.quiz_questions || activeLesson.quiz_questions.length === 0) ? (
                    <div className="p-3 text-center rounded-xl border border-dashed border-slate-200 text-xs text-slate-400">
                      No quiz questions yet for this lesson. Click "+ Add Question" to test comprehension.
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {activeLesson.quiz_questions.map((quest, qIdx) => (
                        <div
                          key={qIdx}
                          className="bg-slate-50/70 border border-slate-200/80 rounded-xl p-3.5 space-y-3"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-[11px] font-bold text-slate-700">
                              Question {qIdx + 1}
                            </span>
                            <button
                              type="button"
                              onClick={() => handleRemoveQuizQuestion(qIdx)}
                              className="text-slate-400 hover:text-rose-500 transition-colors cursor-pointer"
                              title="Delete question"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>

                          <input
                            type="text"
                            placeholder="Enter the quiz question..."
                            value={quest.question}
                            onChange={(e) =>
                              handleUpdateQuizQuestion(qIdx, 'question', e.target.value)
                            }
                            className="w-full text-xs px-3 py-1.5 rounded-lg border border-slate-200 bg-white focus:outline-none focus:border-[#f05a28]"
                          />

                          <div className="space-y-1.5">
                            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                              Options (select radio for correct answer)
                            </span>
                            {quest.options.map((opt, oIdx) => (
                              <div key={oIdx} className="flex items-center gap-2">
                                <input
                                  type="radio"
                                  name={`correct-opt-${activeLessonIdx}-${qIdx}`}
                                  checked={quest.correct_option_index === oIdx}
                                  onChange={() =>
                                    handleUpdateQuizQuestion(qIdx, 'correct_option_index', oIdx)
                                  }
                                  className="text-[#f05a28] focus:ring-[#f05a28] cursor-pointer"
                                />
                                <input
                                  type="text"
                                  placeholder={`Option ${oIdx + 1}`}
                                  value={opt}
                                  onChange={(e) => handleUpdateOption(qIdx, oIdx, e.target.value)}
                                  className="flex-1 text-xs px-2.5 py-1 rounded-lg border border-slate-200 bg-white focus:outline-none focus:border-[#f05a28]"
                                />
                              </div>
                            ))}
                          </div>

                          <input
                            type="text"
                            placeholder="Explanation (shown after the learner submits answer)"
                            value={quest.explanation || ''}
                            onChange={(e) =>
                              handleUpdateQuizQuestion(qIdx, 'explanation', e.target.value)
                            }
                            className="w-full text-xs px-3 py-1 rounded-lg border border-slate-200 bg-white text-slate-600 focus:outline-none focus:border-[#f05a28]"
                          />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </form>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-100 flex items-center justify-between bg-slate-50/70 shrink-0">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            <span>Estimated completion: {estimatedDuration}</span>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-200/70 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-[#f05a28] hover:bg-[#d94b1c] shadow-xs transition-all active:scale-95 flex items-center gap-2 cursor-pointer disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Publishing & Indexing...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Publish & Index Tutorial</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
