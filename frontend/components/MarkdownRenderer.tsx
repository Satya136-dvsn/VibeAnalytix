'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MarkdownRendererProps {
  content: string
  className?: string
}

export default function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      className={className}
      components={{
        h1: ({ children }) => (
          <h1 className="text-2xl font-bold text-on-surface mt-6 mb-4 pb-2 border-b border-outline-variant/20 font-headline">
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-xl font-bold text-on-surface mt-8 mb-3 flex items-center gap-2">
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-base font-semibold text-primary mt-6 mb-2 uppercase tracking-wider text-[13px]">
            {children}
          </h3>
        ),
        p: ({ children }) => (
          <p className="text-on-surface-variant leading-7 mb-4 text-sm">
            {children}
          </p>
        ),
        ul: ({ children }) => (
          <ul className="space-y-2 mb-4 ml-2">
            {children}
          </ul>
        ),
        ol: ({ children }) => (
          <ol className="space-y-2 mb-4 ml-4 list-decimal">
            {children}
          </ol>
        ),
        li: ({ children }) => (
          <li className="text-on-surface-variant text-sm leading-6 flex gap-2">
            <span className="text-primary mt-1.5 flex-shrink-0">▸</span>
            <span>{children}</span>
          </li>
        ),
        code: ({ inline, children, ...props }: any) =>
          inline ? (
            <code className="px-1.5 py-0.5 bg-primary/10 text-primary rounded text-[0.82em] font-mono border border-primary/20">
              {children}
            </code>
          ) : (
            <pre className="bg-surface-container-highest rounded-xl p-4 overflow-x-auto mb-4 border border-outline-variant/10 text-sm font-mono">
              <code className="text-on-surface-variant">{children}</code>
            </pre>
          ),
        strong: ({ children }) => (
          <strong className="text-on-surface font-semibold">{children}</strong>
        ),
        em: ({ children }) => (
          <em className="text-tertiary italic">{children}</em>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-4 border-primary/40 pl-4 my-4 text-on-surface-variant italic bg-primary/5 py-2 rounded-r-lg">
            {children}
          </blockquote>
        ),
        hr: () => <hr className="my-6 border-outline-variant/20" />,
        a: ({ href, children }) => (
          <a href={href} className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">
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
  )
}
