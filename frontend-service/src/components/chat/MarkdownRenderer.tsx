import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Check, Copy } from 'lucide-react';
import { MermaidRenderer } from './MermaidRenderer';

interface MarkdownRendererProps {
  content: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const handleCopy = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => {
      setCopiedCode(null);
    }, 2000);
  };

  return (
    <div className="prose max-w-none text-slate-700 text-sm leading-relaxed min-w-0 break-words [overflow-wrap:anywhere]">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1({ children }) {
            return <h1 className="text-xl font-bold text-slate-900 mt-4 mb-2 break-words [overflow-wrap:anywhere]">{children}</h1>;
          },
          h2({ children }) {
            return <h2 className="text-lg font-bold text-slate-900 mt-3 mb-2 break-words [overflow-wrap:anywhere]">{children}</h2>;
          },
          h3({ children }) {
            return <h3 className="text-base font-semibold text-slate-800 mt-3 mb-1.5 break-words [overflow-wrap:anywhere]">{children}</h3>;
          },
          h4({ children }) {
            return <h4 className="text-sm font-semibold text-slate-800 mt-2 mb-1 break-words [overflow-wrap:anywhere]">{children}</h4>;
          },
          p({ children }) {
            return <p className="mb-2 text-slate-700 leading-normal break-words [overflow-wrap:anywhere]">{children}</p>;
          },
          ul({ children }) {
            return <ul className="list-disc pl-5 my-2 space-y-1 text-slate-700 min-w-0">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="list-decimal pl-5 my-2 space-y-1 text-slate-700 min-w-0">{children}</ol>;
          },
          li({ children }) {
            return <li className="break-words [overflow-wrap:anywhere]">{children}</li>;
          },
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            const language = match ? match[1].toLowerCase() : '';
            const codeString = String(children).replace(/\n$/, '');
            const isInline = !match && !codeString.includes('\n');

            if (isInline) {
              return (
                <code
                  className="bg-amber-50 text-[#f05a28] font-mono text-xs px-1.5 py-0.5 rounded border border-amber-200/70 font-medium break-all [overflow-wrap:anywhere] whitespace-pre-wrap"
                  {...props}
                >
                  {children}
                </code>
              );
            }

            const isMermaid =
              language === 'mermaid' ||
              (!language && /^(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram(-v2)?|erDiagram|journey|gantt|pie|gitGraph|mindmap|timeline)\b/m.test(codeString.trim()));

            if (isMermaid) {
              return <MermaidRenderer chart={codeString} />;
            }

            return (
              <div className="my-3 rounded-xl overflow-hidden border border-slate-700/60 bg-[#1e2433] shadow-md max-w-full min-w-0">
                <div className="flex items-center justify-between px-3.5 py-2 bg-[#151922] border-b border-slate-700/50 text-xs font-mono text-slate-400">
                  <span className="uppercase tracking-wider font-semibold text-amber-400 text-[11px]">
                    {language || 'text'}
                  </span>
                  <button
                    onClick={() => handleCopy(codeString)}
                    type="button"
                    className="flex items-center gap-1.5 text-slate-300 hover:text-white transition-colors px-2 py-1 rounded bg-slate-800/80 hover:bg-slate-700 text-[11px] cursor-pointer"
                    title="Copy code"
                  >
                    {copiedCode === codeString ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                        <span className="text-emerald-400">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
                <div className="overflow-x-auto text-xs">
                  <SyntaxHighlighter
                    style={oneDark}
                    language={language || 'text'}
                    PreTag="div"
                    customStyle={{
                      margin: 0,
                      padding: '1rem',
                      background: 'transparent',
                      fontSize: '0.8125rem',
                      lineHeight: '1.5',
                    }}
                  >
                    {codeString}
                  </SyntaxHighlighter>
                </div>
              </div>
            );
          },
          table({ children }) {
            return (
              <div className="overflow-x-auto my-3 rounded-lg border border-slate-200 shadow-xs max-w-full">
                <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                  {children}
                </table>
              </div>
            );
          },
          th({ children }) {
            return (
              <th className="bg-slate-50 px-3.5 py-2.5 font-semibold text-slate-800">
                {children}
              </th>
            );
          },
          td({ children }) {
            return (
              <td className="px-3.5 py-2 text-slate-600 border-t border-slate-100 break-words">
                {children}
              </td>
            );
          },
          a({ href, children }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noreferrer"
                className="text-[#f05a28] hover:text-[#d94b1c] font-medium underline underline-offset-2 break-all [overflow-wrap:anywhere]"
              >
                {children}
              </a>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownRenderer;
