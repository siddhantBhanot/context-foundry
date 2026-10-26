import React, { useEffect, useState, useId } from 'react';
import mermaid from 'mermaid';
import { Copy, Check, Code, Eye, Workflow, AlertCircle } from 'lucide-react';

interface MermaidRendererProps {
  chart: string;
}

let mermaidInitialized = false;

function initMermaid() {
  if (mermaidInitialized) return;
  try {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'loose',
      suppressErrorRendering: true,
      theme: 'neutral',
      themeVariables: {
        primaryColor: '#fff7ed', // orange-50
        primaryTextColor: '#1e293b', // slate-800
        primaryBorderColor: '#f97316', // orange-500
        lineColor: '#64748b', // slate-500
        secondaryColor: '#f8fafc', // slate-50
        tertiaryColor: '#f1f5f9', // slate-100
        noteBkgColor: '#fef3c7',
        noteTextColor: '#78350f',
        fontFamily: 'ui-sans-serif, system-ui, -apple-system, sans-serif',
        fontSize: '13px',
      },
      fontFamily: 'ui-sans-serif, system-ui, -apple-system, sans-serif',
    });
    mermaid.setParseErrorHandler(() => {});
    mermaidInitialized = true;
  } catch (err) {
    console.error('Failed to initialize mermaid:', err);
  }
}

/**
 * Intelligently sanitizes and repairs LLM-generated Mermaid diagrams:
 * 1. Strips markdown fences and extraneous wrappers.
 * 2. Normalizes Unicode dashes, em-dashes, en-dashes, and unicode arrows to valid Mermaid connectors.
 * 3. Replaces single ASCII arrows `->` with standard `-->`.
 * 4. Auto-quotes node labels containing punctuation, parentheses, slashes, or ampersands (`&`, `/`, `()`).
 * 5. Quotes unquoted subgraph labels containing spaces or special characters.
 * 6. Ensures unclosed subgraphs are balanced with `end`.
 * 7. Ensures missing directions (e.g. `flowchart` -> `flowchart TD`) are filled in.
 */
export function sanitizeMermaidChart(raw: string): string {
  if (!raw) return '';
  let text = raw.trim();

  // 1. Strip markdown code block wrappers if present
  text = text.replace(/^```[a-zA-Z]*\s*\n?/, '').replace(/\n?\s*```$/, '').trim();

  // 2. Strip invisible zero-width characters and normalize unicode spaces
  text = text.replace(/[\u200B\u200C\u200D\uFEFF]/g, '');
  text = text.replace(/[\u00A0\u202F\u2007\u2060]/g, ' ');

  // 3. Diagram-type awareness:
  // Sequence diagrams, class diagrams, state diagrams, and ER diagrams have different grammars
  // and MUST NOT have flowchart node-shape regexes applied to them.
  const isSequence = /^\s*sequenceDiagram\b/m.test(text);
  const isClass = /^\s*classDiagram\b/m.test(text);
  const isState = /^\s*stateDiagram(?:-v2)?\b/m.test(text);
  const isEr = /^\s*erDiagram\b/m.test(text);

  if (isSequence || isClass || isState || isEr) {
    return text;
  }

  // 4. Normalize Unicode dashes & arrows
  // Non-breaking hyphen (\u2011), Hyphen (\u2010), Figure dash (\u2012), En-dash (\u2013), Em-dash (\u2014), Horizontal bar (\u2015), Box-drawings light horizontal (\u2500)
  text = text.replace(/[\u2010\u2011\u2012\u2013\u2014\u2015\u2500]+>/g, '-->');
  text = text.replace(/<[\u2010\u2011\u2012\u2013\u2014\u2015\u2500]+>/g, '<-->');
  text = text.replace(/<[\u2010\u2011\u2012\u2013\u2014\u2500]+/g, '<--');
  text = text.replace(/[\u2010\u2011\u2012\u2013\u2014\u2015\u2500]{2,}/g, '--');
  text = text.replace(/[\u2010\u2011\u2012\u2013\u2014\u2500]/g, '-');
  // Standalone unicode right arrows: →, ➔, ➜, ⟶
  text = text.replace(/[\u2192\u2794\u279c\u27f6]/g, '-->');
  // Standalone unicode double arrows: ⇒, ⟹
  text = text.replace(/[\u21d2\u27f9]/g, '==>');

  // 5. Single dash arrow: replace " -> " or "] -> " or ") -> " with " --> "
  text = text.replace(/(\s)->(\s)/g, '$1-->$2');
  text = text.replace(/(\])\s*->(\s)/g, '$1 -->$2');
  text = text.replace(/(\))\s*->(\s)/g, '$1 -->$2');
  text = text.replace(/(\})\s*->(\s)/g, '$1 -->$2');

  // 6. Direction validation
  // If line starts with bare "flowchart" or "graph" without direction, append TD
  text = text.replace(/^(flowchart|graph)\s*$/m, '$1 TD');

  // 7. Protect existing double-quoted strings with tokens
  // This is CRITICAL: Mermaid nodes like `B["Identity Collection\n(OVDs + PAN / Form 60)"]`
  // must not have their inner parentheses matched by round-bracket node regexes!
  const stringTokens: string[] = [];
  text = text.replace(/"([^"\\]*(?:\\.[^"\\]*)*)"/g, (_match, inner) => {
    const idx = stringTokens.length;
    // Normalize newlines inside strings to literal \n so line splitting doesn't break strings
    const normalized = inner.replace(/\r?\n/g, '\\n');
    stringTokens.push(normalized);
    return `"___MERMAID_STR_${idx}___"`;
  });

  // 8. Line-by-line label quoting and subgraph normalization
  const lines = text.split('\n');
  let openSubgraphs = 0;

  const sanitizedLines = lines.map((line) => {
    let l = line;
    const trimmed = l.trim();

    // Skip comments
    if (trimmed.startsWith('%%')) return l;

    // Track and sanitize subgraphs
    if (/^\s*subgraph\b/i.test(l)) {
      openSubgraphs++;
      l = l.replace(/^(\s*subgraph\s+)(.+)$/i, (match, prefix, rest) => {
        const title = rest.trim();
        if (
          title.includes('___MERMAID_STR_') ||
          /^[a-zA-Z0-9_-]+\s*\[.+\]$/.test(title) ||
          (title.startsWith('"') && title.endsWith('"')) ||
          (title.startsWith('[') && title.endsWith(']'))
        ) {
          return match;
        }
        if (/[^a-zA-Z0-9_-]/.test(title)) {
          return `${prefix}"${title.replace(/"/g, "'")}"`;
        }
        return match;
      });
      return l;
    }

    if (/^\s*end\b/i.test(l)) {
      if (openSubgraphs > 0) openSubgraphs--;
      return l;
    }

    // Edge labels: |label| -> |"label"|
    l = l.replace(/\|([^|\n]+)\|/g, (match, content) => {
      const cTrim = content.trim();
      if (
        cTrim.includes('___MERMAID_STR_') ||
        (cTrim.startsWith('"') && cTrim.endsWith('"')) ||
        (cTrim.startsWith("'") && cTrim.endsWith("'"))
      ) {
        return match;
      }
      const safe = cTrim.replace(/"/g, "'");
      return `|"${safe}"|`;
    });

    const quoteContent = (content: string) => {
      const cTrim = content.trim();
      if (
        cTrim.includes('___MERMAID_STR_') ||
        (cTrim.startsWith('"') && cTrim.endsWith('"')) ||
        (cTrim.startsWith("'") && cTrim.endsWith("'"))
      ) {
        return cTrim;
      }
      const safe = cTrim.replace(/"/g, "'");
      return `"${safe}"`;
    };

    // Compound shapes first:
    // Cylinder: ID[(content)]
    l = l.replace(/([a-zA-Z0-9_-]+)\[\(([^)\n]+)\)\]/g, (_match, id, content) => {
      return `${id}[(${quoteContent(content)})]`;
    });

    // Stadium: ID([content])
    l = l.replace(/([a-zA-Z0-9_-]+)\(\[([^\]\n]+)\]\)/g, (_match, id, content) => {
      return `${id}([${quoteContent(content)}])`;
    });

    // Subroutine: ID[[content]]
    l = l.replace(/([a-zA-Z0-9_-]+)\[\[([^\]\n]+)\]\]/g, (_match, id, content) => {
      return `${id}[[${quoteContent(content)}]]`;
    });

    // Hexagon: ID{{content}}
    l = l.replace(/([a-zA-Z0-9_-]+)\{\{([^}\n]+)\}\}/g, (_match, id, content) => {
      return `${id}{{${quoteContent(content)}}}`;
    });

    // Diamond: ID{content}
    l = l.replace(/([a-zA-Z0-9_-]+)\{([^}\n]+)\}/g, (_match, id, content) => {
      return `${id}{${quoteContent(content)}}`;
    });

    // Round: ID(content)
    l = l.replace(/([a-zA-Z0-9_-]+)\(([^)\n]+)\)/g, (match, id, content) => {
      if (['subgraph', 'classDef', 'style', 'click'].includes(id)) return match;
      return `${id}(${quoteContent(content)})`;
    });

    // Rectangle: ID[content]
    l = l.replace(/([a-zA-Z0-9_-]+)\[([^\]\n]+)\]/g, (_match, id, content) => {
      return `${id}[${quoteContent(content)}]`;
    });

    return l;
  });

  // Balance any missing `end` for unclosed subgraphs
  while (openSubgraphs > 0) {
    sanitizedLines.push('  end');
    openSubgraphs--;
  }

  let result = sanitizedLines.join('\n');

  // Restore protected strings
  result = result.replace(/"___MERMAID_STR_(\d+)___"/g, (_match, idx) => {
    return `"${stringTokens[Number(idx)]}"`;
  });

  return result;
}

export const MermaidRenderer: React.FC<MermaidRendererProps> = ({ chart }) => {
  const reactId = useId();
  // Generate clean DOM-compatible ID
  const elementId = 'mermaid-' + reactId.replace(/[^a-zA-Z0-9_-]/g, '');

  const [svg, setSvg] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isRendering, setIsRendering] = useState<boolean>(true);
  const [showCode, setShowCode] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    initMermaid();
    let isCancelled = false;

    const renderChart = async () => {
      const cleanChart = sanitizeMermaidChart(chart);
      if (!cleanChart) {
        setSvg('');
        setIsRendering(false);
        return;
      }

      setIsRendering(true);
      setError(null);

      try {
        // Unique container ID per render cycle to avoid Mermaid collision
        const uniqueRenderId = `${elementId}-${Date.now()}`;
        let renderedSvg: string | null = null;

        try {
          const res = await mermaid.render(uniqueRenderId, cleanChart);
          renderedSvg = res.svg;
        } catch (firstErr) {
          // If first render fails, attempt alternate graph/flowchart keyword or basic fallback
          const altChart = cleanChart.startsWith('flowchart')
            ? cleanChart.replace(/^flowchart\b/, 'graph')
            : cleanChart.startsWith('graph')
            ? cleanChart.replace(/^graph\b/, 'flowchart')
            : cleanChart;

          const retryRenderId = `${elementId}-retry-${Date.now()}`;
          const res = await mermaid.render(retryRenderId, altChart);
          renderedSvg = res.svg;
        }

        if (!isCancelled && renderedSvg) {
          setSvg(renderedSvg);
          setError(null);
          setIsRendering(false);
        }
      } catch (err: any) {
        if (!isCancelled) {
          console.warn('Mermaid syntax error or streaming incomplete:', err);
          setError(err?.message || 'Invalid or incomplete diagram definition');
          setIsRendering(false);
        }
        // Remove any temporary error element created by Mermaid in body
        document.querySelectorAll(`svg[id^="d${elementId}"], svg[id^="dmermaid-"]`).forEach((el) => {
          el.remove();
        });
      }
    };

    renderChart();

    return () => {
      isCancelled = true;
    };
  }, [chart, elementId]);

  const handleCopy = () => {
    navigator.clipboard.writeText(chart);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // If there's an error (e.g. malformed syntax or token streaming midway),
  // fallback gracefully to showing the code with an indicator instead of breaking
  if (error && !svg) {
    return (
      <div className="my-4 rounded-xl border border-amber-200/80 bg-amber-50/40 p-4 shadow-xs">
        <div className="flex items-center justify-between pb-2 mb-2 border-b border-amber-200/60 text-xs">
          <div className="flex items-center gap-1.5 font-semibold text-amber-900">
            <AlertCircle className="w-4 h-4 text-amber-600" />
            <span>Diagram Preview (Draft)</span>
          </div>
          <button
            onClick={handleCopy}
            type="button"
            className="flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium text-amber-800 hover:bg-amber-100 transition-colors cursor-pointer"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
        <pre className="text-xs font-mono text-slate-700 overflow-x-auto whitespace-pre p-2 bg-white/80 rounded-lg border border-amber-100">
          {chart}
        </pre>
      </div>
    );
  }

  return (
    <div className="my-4 rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden transition-all">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-50/80 border-b border-slate-200/80 text-xs text-slate-600">
        <div className="flex items-center gap-2 font-semibold text-slate-800">
          <Workflow className="w-4 h-4 text-[#f05a28]" />
          <span>Architecture & Flow Diagram</span>
        </div>

        <div className="flex items-center gap-2">
          {/* Toggle between rendered diagram and code */}
          <button
            onClick={() => setShowCode(!showCode)}
            type="button"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 transition-colors text-[11px] font-medium cursor-pointer shadow-2xs"
            title={showCode ? 'View Diagram' : 'View Code'}
          >
            {showCode ? (
              <>
                <Eye className="w-3.5 h-3.5 text-[#f05a28]" />
                <span>Diagram</span>
              </>
            ) : (
              <>
                <Code className="w-3.5 h-3.5 text-slate-500" />
                <span>Source</span>
              </>
            )}
          </button>

          {/* Copy button */}
          <button
            onClick={handleCopy}
            type="button"
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 transition-colors text-[11px] font-medium cursor-pointer shadow-2xs"
            title="Copy Mermaid code"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-emerald-700 font-semibold">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-slate-500" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="p-4 sm:p-6 bg-linear-to-b from-white to-slate-50/40">
        {showCode ? (
          <div className="rounded-xl overflow-hidden border border-slate-700/60 bg-[#1e2433]">
            <pre className="p-4 text-xs font-mono text-slate-200 overflow-x-auto whitespace-pre leading-relaxed">
              {chart}
            </pre>
          </div>
        ) : isRendering && !svg ? (
          <div className="flex items-center justify-center py-8 text-xs text-slate-400 gap-2">
            <div className="w-4 h-4 border-2 border-[#f05a28] border-t-transparent rounded-full animate-spin" />
            <span>Rendering diagram...</span>
          </div>
        ) : (
          <div
            className="w-full overflow-x-auto flex justify-center items-center py-2 [&>svg]:max-w-full [&>svg]:h-auto [&>svg]:mx-auto transition-opacity duration-200"
            dangerouslySetInnerHTML={{ __html: svg }}
          />
        )}
      </div>
    </div>
  );
};

export default MermaidRenderer;
