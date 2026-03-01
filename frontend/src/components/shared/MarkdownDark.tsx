import ReactMarkdown from "react-markdown";

interface MarkdownDarkProps {
  children: string;
  className?: string;
}

/**
 * Dark-themed markdown renderer for use on dark backgrounds (e.g. ThinkingSidebar).
 */
export default function MarkdownDark({ children, className = "text-xs" }: MarkdownDarkProps) {
  return (
    <ReactMarkdown
      components={{
        h1: ({ children }) => (
          <h1 className="text-sm font-bold text-slate-200 mt-2 mb-1 first:mt-0">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-xs font-semibold text-slate-200 mt-2 mb-1 first:mt-0">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-xs font-semibold text-slate-300 mt-1.5 mb-0.5 first:mt-0">{children}</h3>
        ),
        p: ({ children }) => (
          <p className={`${className} leading-relaxed mb-1.5 last:mb-0`}>{children}</p>
        ),
        ul: ({ children }) => (
          <ul className="list-disc list-outside pl-4 mb-1.5 space-y-0.5 last:mb-0">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal list-outside pl-4 mb-1.5 space-y-0.5 last:mb-0">{children}</ol>
        ),
        li: ({ children }) => (
          <li className={`${className} leading-relaxed`}>{children}</li>
        ),
        strong: ({ children }) => (
          <strong className="font-semibold text-slate-200">{children}</strong>
        ),
        code: ({ className: codeClass, children, ...rest }) => {
          const isBlock = codeClass?.startsWith("language-");
          if (isBlock) {
            return <code className={`${codeClass ?? ""} text-xs`} {...rest}>{children}</code>;
          }
          return (
            <code className="px-1 py-0.5 rounded bg-slate-700/60 text-slate-300 text-xs font-mono">
              {children}
            </code>
          );
        },
        pre: ({ children }) => (
          <pre className="bg-slate-950/50 text-slate-300 rounded p-2 overflow-x-auto mb-1.5 text-xs leading-relaxed last:mb-0">
            {children}
          </pre>
        ),
        table: ({ children }) => (
          <div className="overflow-x-auto mb-1.5 last:mb-0">
            <table className="min-w-full text-xs border-collapse">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="border-b border-slate-700">{children}</thead>
        ),
        th: ({ children }) => (
          <th className="px-2 py-1 text-left font-semibold text-slate-300 border-b border-slate-700">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="px-2 py-1 text-slate-400 border-b border-slate-800">{children}</td>
        ),
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
