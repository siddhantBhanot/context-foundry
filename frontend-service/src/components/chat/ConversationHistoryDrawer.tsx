import { useEffect, useState } from 'react';
import { Clock, MessageSquare, Plus, X } from 'lucide-react';
import apiClient from '@/lib/api/client';
import type { ConversationSummary } from '@/types';

interface ConversationHistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  currentConversationId?: string | null;
  onSelectConversation: (conversationId: string) => void;
  onNewChat: () => void;
}

export function ConversationHistoryDrawer({
  isOpen,
  onClose,
  currentConversationId,
  onSelectConversation,
  onNewChat,
}: ConversationHistoryDrawerProps) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadConversations = async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.listConversations(undefined, 30);
      setConversations(data);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadConversations();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/40 backdrop-blur-xs">
      <div className="bg-white w-full max-w-sm h-full shadow-2xl flex flex-col p-6 space-y-4 animate-in slide-in-from-right duration-200">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-[#f05a28]" />
            <h3 className="font-bold text-sm text-slate-900">Conversation History</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <button
          onClick={() => {
            onNewChat();
            onClose();
          }}
          className="w-full py-2.5 px-4 bg-slate-100 hover:bg-slate-200/70 text-slate-800 text-xs font-semibold rounded-2xl flex items-center justify-center gap-2 transition-colors cursor-pointer border border-slate-200/80"
        >
          <Plus className="w-3.5 h-3.5 text-[#f05a28]" />
          <span>Start New Conversation</span>
        </button>

        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          {isLoading ? (
            <div className="py-8 text-center text-xs text-slate-400">Loading sessions...</div>
          ) : conversations.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-400">No past conversations found.</div>
          ) : (
            conversations.map((c) => {
              const isSelected = c.id === currentConversationId;
              const dateStr = new Date(c.updated_at).toLocaleDateString([], {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              });

              return (
                <div
                  key={c.id}
                  onClick={() => {
                    onSelectConversation(c.id);
                    onClose();
                  }}
                  className={`p-3 rounded-2xl border text-left cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-orange-50/70 border-orange-200 shadow-xs'
                      : 'bg-white hover:bg-slate-50 border-slate-200/80 hover:border-slate-300'
                  }`}
                >
                  <p className="text-xs font-semibold text-slate-800 line-clamp-2 leading-snug">
                    {c.title || 'Untitled conversation'}
                  </p>
                  <div className="flex items-center justify-between mt-2 text-[10px] text-slate-400 font-mono">
                    <span className="truncate max-w-[140px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                      {c.service}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-300" />
                      {dateStr}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
