import { useState } from 'react';
import { Check, Copy, GitBranch, Lock, Share2, X } from 'lucide-react';

interface ShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  conversationId?: string | null;
  shareToken: string | null;
  isLoading: boolean;
}

export function ShareModal({
  isOpen,
  onClose,
  shareToken,
  isLoading,
}: ShareModalProps) {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const shareUrl = typeof window !== 'undefined' && shareToken
    ? `${window.location.origin}/?share=${shareToken}`
    : '';

  const handleCopy = async () => {
    if (!shareUrl) return;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // Fallback
      const input = document.getElementById('share-link-input') as HTMLInputElement;
      if (input) {
        input.select();
        document.execCommand('copy');
        setCopied(true);
        setTimeout(() => setCopied(false), 2500);
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white rounded-[28px] md:rounded-[36px] shadow-xl border border-slate-100 max-w-lg w-full p-6 sm:p-8 relative">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-6 right-6 p-2 rounded-full text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
          title="Close modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-2xl bg-orange-50 border border-orange-100 flex items-center justify-center text-[#f05a28] shrink-0">
            <Share2 className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-black text-slate-900 tracking-tight">
              Share Conversation
            </h3>
            <p className="text-xs text-slate-500">
              Generate a secure link for team collaboration
            </p>
          </div>
        </div>

        {isLoading ? (
          <div className="py-8 flex flex-col items-center justify-center gap-3">
            <div className="w-7 h-7 border-2 border-[#f05a28]/20 border-t-[#f05a28] rounded-full animate-spin" />
            <span className="text-xs font-semibold text-slate-500">Generating secure share token...</span>
          </div>
        ) : shareToken ? (
          <div className="space-y-5">
            {/* Share URL Input & Copy Button */}
            <div>
              <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-2">
                Shareable Link
              </label>
              <div className="flex items-center gap-2">
                <input
                  id="share-link-input"
                  type="text"
                  readOnly
                  value={shareUrl}
                  className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-xs text-slate-800 font-mono focus:bg-white focus:outline-none focus:border-[#f05a28] select-all transition-all"
                />
                <button
                  type="button"
                  onClick={handleCopy}
                  className={`flex items-center gap-1.5 px-4 py-2.5 rounded-xl font-semibold text-xs transition-all shrink-0 cursor-pointer shadow-xs ${
                    copied
                      ? 'bg-emerald-600 text-white'
                      : 'bg-[#f05a28] hover:bg-[#d94b1c] active:scale-98 text-white'
                  }`}
                >
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      <span>Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copy Link</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Fork on Reply Explanation Card */}
            <div className="p-4 rounded-2xl bg-[#edf3f8]/70 border border-slate-200/80 space-y-2.5 text-xs">
              <div className="flex items-start gap-2.5 text-slate-800 font-semibold">
                <GitBranch className="w-4 h-4 text-[#f05a28] shrink-0 mt-0.5" />
                <span>Automatic Branching (Fork-on-Reply)</span>
              </div>
              <p className="text-[11px] leading-relaxed text-slate-600 pl-6.5">
                Any engineer with this link can view your conversation and verified source citations. When another engineer replies, the thread will <strong className="text-slate-800 font-semibold">automatically fork into a new conversation</strong> in their account. Your original thread will remain untouched.
              </p>
              <div className="pt-2 border-t border-slate-200/60 flex items-center gap-1.5 text-[10px] text-slate-500 pl-6.5">
                <Lock className="w-3 h-3 text-slate-400" />
                <span>Requires an authenticated ContextFoundry engineer account</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="py-6 text-center text-xs text-slate-500">
            Unable to generate share link for this conversation.
          </div>
        )}

        {/* Modal Footer */}
        <div className="mt-6 pt-4 border-t border-slate-100 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-full text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
