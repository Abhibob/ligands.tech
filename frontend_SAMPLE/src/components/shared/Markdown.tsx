import ReactMarkdown from "react-markdown";

interface MarkdownProps {
  children: string;
  /** Base text size class. Defaults to "text-sm" */
  className?: string;
}

/**
 * Renders a markdown string with Tailwind prose-like styling.
 *
 * Covers headings, paragraphs, lists, code blocks, inline code,
 * bold/italic, links, horizontal rules, and tables.
 */
export default function Markdown({ children, className = "text-sm" }: MarkdownProps) {
  return (
    <ReactMarkdown
      components={{
        h1: ({ children }) => (
          <h1 className="text-xl font-bold text-slate-900 mt-4 mb-2 first:mt-0">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-lg font-semibold text-slate-900 mt-4 mb-2 first:mt-0">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-base font-semibold text-slate-800 mt-3 mb-1 first:mt-0">{children}</h3>
        ),
        h4: ({ children }) => (
          <h4 className="text-sm font-semibold text-slate-800 mt-2 mb-1 first:mt-0">{children}</h4>
        ),
        p: ({ children }) => (
          <p className={`${className} text-slate-600 leading-relaxed mb-3 last:mb-0`}>{children}</p>
        ),
        ul: ({ children }) => (
          <ul className="list-disc list-outside pl-5 mb-3 space-y-1 last:mb-0">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal list-outside pl-5 mb-3 space-y-1 last:mb-0">{children}</ol>
        ),
        li: ({ children }) => (
          <li className={`${className} text-slate-600 leading-relaxed`}>{children}</li>
        ),
        strong: ({ children }) => (
          <strong className="font-semibold text-slate-800">{children}</strong>
        ),
        em: ({ children }) => <em className="italic">{children}</em>,
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-teal-600 hover:text-teal-700 underline underline-offset-2"
          >
            {children}
          </a>
        ),
        code: ({ className: codeClass, children, ...rest }) => {
          // Detect code blocks (has language- class from react-markdown) vs inline
          const isBlock = codeClass?.startsWith("language-");
          if (isBlock) {
            return (
              <code className={`${codeClass ?? ""} text-xs`} {...rest}>
                {children}
              </code>
            );
          }
          return (
            <code className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 text-xs font-mono">
              {children}
            </code>
          );
        },
        pre: ({ children }) => (
          <pre className="bg-slate-900 text-slate-100 rounded-lg p-4 overflow-x-auto mb-3 text-xs leading-relaxed last:mb-0">
            {children}
          </pre>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-3 border-slate-300 pl-4 text-slate-500 italic mb-3 last:mb-0">
            {children}
          </blockquote>
        ),
        hr: () => <hr className="border-slate-200 my-4" />,
        table: ({ children }) => (
          <div className="overflow-x-auto mb-3 last:mb-0">
            <table className="min-w-full text-xs border-collapse">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-slate-50 border-b border-slate-200">{children}</thead>
        ),
        th: ({ children }) => (
          <th className="px-3 py-2 text-left font-semibold text-slate-700 border-b border-slate-200">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="px-3 py-1.5 text-slate-600 border-b border-slate-100">{children}</td>
        ),
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
