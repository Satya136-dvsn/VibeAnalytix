'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MarkdownRendererProps {
  content: string
  className?: string
}

/**
 * Bulletproof markdown renderer compatible with react-markdown v9.
 *
 * v9 changes:
 *  - Removed `className` prop on <ReactMarkdown>
 *  - Removed `inline` prop from `code` component
 *
 * Strategy: override `pre` to style the block wrapper and `code` to handle
 * both inline and block cases. Block code always has a `language-xxx` className
 * from remark-gfm; inline code has no className. We use that to differentiate.
 */
export default function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // ── Headings ──────────────────────────────────────────────────────────
          h1: ({ children }) => (
            <h1 className="text-2xl font-bold text-on-surface mt-6 mb-4 pb-2 border-b border-outline-variant/20">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-xl font-bold text-on-surface mt-8 mb-3">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-[13px] font-semibold text-primary mt-6 mb-2 uppercase tracking-wider">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-sm font-semibold text-on-surface mt-4 mb-2">
              {children}
            </h4>
          ),

          // ── Text elements ─────────────────────────────────────────────────────
          p: ({ children }) => (
            <p className="text-on-surface-variant leading-7 mb-4 text-sm">
              {children}
            </p>
          ),
          strong: ({ children }) => (
            <strong className="text-on-surface font-semibold">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="text-tertiary italic">{children}</em>
          ),

          // ── Lists ─────────────────────────────────────────────────────────────
          ul: ({ children }) => (
            <ul className="mb-4 ml-1 space-y-1.5">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="mb-4 ml-4 space-y-1.5 list-decimal marker:text-primary">{children}</ol>
          ),
          li: ({ children }) => (
            <li className="text-on-surface-variant text-sm leading-6 flex gap-2 items-start">
              <span className="text-primary mt-[5px] flex-shrink-0 text-[10px]">▸</span>
              <span>{children}</span>
            </li>
          ),

          // ── Code — block vs inline ────────────────────────────────────────────
          // react-markdown v9: `pre` wraps block code; bare `code` = inline code.
          // Block code nodes always arrive inside a `pre`, so we style `pre` and
          // let `code` inside it render unstyled. We detect inline by the absence
          // of a language className.
          pre: ({ children }) => (
            <pre className="bg-[#0d1117] rounded-xl p-4 overflow-x-auto mb-4 border border-outline-variant/10 text-sm font-mono text-green-300">
              {children}
            </pre>
          ),
          code: ({ className: cls, children }) => {
            const isBlock = Boolean(cls) // language-xxx present means fenced block
            if (isBlock) {
              // Inside a `pre` — just render the code tag cleanly
              return <code className={cls}>{children}</code>
            }
            // Inline code
            return (
              <code className="px-1.5 py-0.5 bg-primary/10 text-primary rounded text-[0.82em] font-mono border border-primary/20 whitespace-nowrap">
                {children}
              </code>
            )
          },

          // ── Other elements ────────────────────────────────────────────────────
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-primary/40 pl-4 my-4 text-on-surface-variant italic bg-primary/5 py-2 rounded-r-lg">
              {children}
            </blockquote>
          ),
          hr: () => <hr className="my-6 border-outline-variant/20" />,
          a: ({ href, children }) => (
            <a
              href={href}
              className="text-primary hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              {children}
            </a>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto mb-4">
              <table className="w-full text-sm border-collapse border border-outline-variant/20 rounded-lg overflow-hidden">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="bg-surface-container px-4 py-2 text-left font-semibold text-on-surface border-b border-outline-variant/20 text-xs uppercase tracking-wider">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-4 py-2 text-on-surface-variant border-b border-outline-variant/10 text-sm">
              {children}
            </td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
