import { useState } from 'react';
import { Check, MessageSquare, ThumbsDown, ThumbsUp } from 'lucide-react';
import apiClient from '@/lib/api/client';

interface FeedbackControlsProps {
  messageId: string;
  conversationId: string;
  initialRating?: 'positive' | 'negative' | null;
}

export function FeedbackControls({
  messageId,
  conversationId,
  initialRating = null,
}: FeedbackControlsProps) {
  const [rating, setRating] = useState<'positive' | 'negative' | null>(initialRating);
  const [showCommentBox, setShowCommentBox] = useState(false);
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleRate = async (newRating: 'positive' | 'negative') => {
    if (rating === newRating) return;
    setRating(newRating);
    setIsSubmitting(true);

    try {
      await apiClient.submitFeedback({
        message_id: messageId,
        conversation_id: conversationId,
        rating: newRating,
        comment: comment.trim() || undefined,
      });
      setSubmitted(true);
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSendComment = async () => {
    if (!rating || !comment.trim()) return;
    setIsSubmitting(true);

    try {
      await apiClient.submitFeedback({
        message_id: messageId,
        conversation_id: conversationId,
        rating,
        comment: comment.trim(),
      });
      setSubmitted(true);
      setShowCommentBox(false);
    } catch (err) {
      console.error('Failed to update feedback with comment:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-1.5 pt-2 border-t border-slate-100">
      <div className="flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-slate-400">Was this answer accurate?</span>
          
          <button
            onClick={() => handleRate('positive')}
            disabled={isSubmitting}
            className={`p-1 rounded-md transition-all cursor-pointer flex items-center gap-1 text-[11px] ${
              rating === 'positive'
                ? 'bg-emerald-100 text-emerald-700 font-semibold'
                : 'hover:bg-slate-100 text-slate-400 hover:text-slate-700'
            }`}
            title="Accurate and helpful"
          >
            <ThumbsUp className={`w-3.5 h-3.5 ${rating === 'positive' ? 'fill-emerald-600' : ''}`} />
            {rating === 'positive' && <span>Helpful</span>}
          </button>

          <button
            onClick={() => {
              handleRate('negative');
              setShowCommentBox(true);
            }}
            disabled={isSubmitting}
            className={`p-1 rounded-md transition-all cursor-pointer flex items-center gap-1 text-[11px] ${
              rating === 'negative'
                ? 'bg-rose-100 text-rose-700 font-semibold'
                : 'hover:bg-slate-100 text-slate-400 hover:text-slate-700'
            }`}
            title="Inaccurate or incomplete"
          >
            <ThumbsDown className={`w-3.5 h-3.5 ${rating === 'negative' ? 'fill-rose-600' : ''}`} />
            {rating === 'negative' && <span>Issues</span>}
          </button>

          {rating && !submitted && (
            <button
              onClick={() => setShowCommentBox(!showCommentBox)}
              className="p-1 text-[11px] text-slate-400 hover:text-slate-600 flex items-center gap-1 cursor-pointer"
              title="Add a comment"
            >
              <MessageSquare className="w-3 h-3" />
              <span>Comment</span>
            </button>
          )}

          {submitted && (
            <span className="inline-flex items-center gap-1 text-[11px] text-emerald-600 font-medium ml-1">
              <Check className="w-3 h-3" /> Recorded
            </span>
          )}
        </div>
      </div>

      {showCommentBox && (
        <div className="mt-1.5 flex items-center gap-2 p-1.5 bg-slate-50 rounded-xl border border-slate-200">
          <input
            type="text"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                handleSendComment();
              }
            }}
            placeholder="Tell us what was missing or incorrect..."
            className="flex-1 text-xs bg-transparent px-2 py-1 text-slate-700 placeholder-slate-400 focus:outline-none"
          />
          <button
            onClick={handleSendComment}
            disabled={!comment.trim() || isSubmitting}
            className="px-2.5 py-1 text-[11px] font-semibold bg-slate-900 hover:bg-slate-800 text-white rounded-lg transition-colors cursor-pointer disabled:opacity-50"
          >
            Send
          </button>
        </div>
      )}
    </div>
  );
}
