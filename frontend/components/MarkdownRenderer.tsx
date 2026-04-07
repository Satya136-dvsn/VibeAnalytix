'use client'

interface Props {
  content: string
  className?: string
}

/**
 * Zero-dependency Markdown renderer.
 * Handles: headings, bold, italic, inline code, code blocks, lists, horizontal rules, links.
 * No external library — no version-conflict issues.
 */
export default function MarkdownRenderer({ content, className }: Props) {
  const html = parseMarkdown(content || '')
  return (
    <div
      className={className}
      dangerouslySetInnerHTML={{ __html: html }}
      style={{ lineHeight: 1.75 }}
    />
  )
}

function parseMarkdown(md: string): string {
  const lines = md.split('\n')
  const output: string[] = []
  let inCodeBlock = false
  let codeLang = ''
  let codeLines: string[] = []
  let inList = false

  const closeList = () => {
    if (inList) {
      output.push('</ul>')
      inList = false
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i]

    // ── Fenced code blocks ────────────────────────────────────────
    if (raw.trimStart().startsWith('```')) {
      if (!inCodeBlock) {
        closeList()
        inCodeBlock = true
        codeLang = raw.trim().slice(3).trim()
        codeLines = []
      } else {
        inCodeBlock = false
        const code = escapeHtml(codeLines.join('\n'))
        output.push(
          `<pre style="background:#0d1117;border-radius:10px;padding:16px;overflow-x:auto;margin-bottom:16px;border:1px solid rgba(255,255,255,0.08)"><code style="color:#7dd3a8;font-family:monospace;font-size:13px">${code}</code></pre>`
        )
      }
      continue
    }

    if (inCodeBlock) {
      codeLines.push(raw)
      continue
    }

    // ── Headings ──────────────────────────────────────────────────
    if (raw.startsWith('#### ')) {
      closeList()
      output.push(`<h4 style="font-size:13px;font-weight:600;color:var(--md-on-surface,#e2e8f0);margin:16px 0 8px">${inlineFormat(raw.slice(5))}</h4>`)
      continue
    }
    if (raw.startsWith('### ')) {
      closeList()
      output.push(`<h3 style="font-size:12px;font-weight:700;color:#a78bfa;margin:24px 0 8px;text-transform:uppercase;letter-spacing:.08em">${inlineFormat(raw.slice(4))}</h3>`)
      continue
    }
    if (raw.startsWith('## ')) {
      closeList()
      output.push(`<h2 style="font-size:18px;font-weight:700;color:#f1f5f9;margin:32px 0 12px;padding-bottom:6px;border-bottom:1px solid rgba(255,255,255,0.08)">${inlineFormat(raw.slice(3))}</h2>`)
      continue
    }
    if (raw.startsWith('# ')) {
      closeList()
      output.push(`<h1 style="font-size:22px;font-weight:700;color:#f8fafc;margin:16px 0 12px;padding-bottom:8px;border-bottom:1px solid rgba(255,255,255,0.12)">${inlineFormat(raw.slice(2))}</h1>`)
      continue
    }

    // ── Horizontal rule ───────────────────────────────────────────
    if (raw.trim() === '---' || raw.trim() === '***' || raw.trim() === '___') {
      closeList()
      output.push('<hr style="border:none;border-top:1px solid rgba(255,255,255,0.1);margin:24px 0" />')
      continue
    }

    // ── List items ────────────────────────────────────────────────
    const listMatch = raw.match(/^(\s*)([-*+]|\d+\.) (.*)/)
    if (listMatch) {
      if (!inList) {
        output.push('<ul style="list-style:none;padding:0;margin:0 0 16px">')
        inList = true
      }
      output.push(
        `<li style="display:flex;gap:8px;align-items:flex-start;margin-bottom:6px;font-size:13px;color:#94a3b8;line-height:1.7"><span style="color:#a78bfa;flex-shrink:0;margin-top:4px">▸</span><span>${inlineFormat(listMatch[3])}</span></li>`
      )
      continue
    }

    // ── Blank line ────────────────────────────────────────────────
    if (raw.trim() === '') {
      closeList()
      output.push('<div style="margin-bottom:8px"></div>')
      continue
    }

    // ── Paragraph ─────────────────────────────────────────────────
    closeList()
    output.push(
      `<p style="color:#94a3b8;font-size:13px;line-height:1.75;margin-bottom:12px">${inlineFormat(raw)}</p>`
    )
  }

  closeList()
  return output.join('\n')
}

function inlineFormat(text: string): string {
  // Always escape user-controlled text first to prevent raw HTML injection.
  text = escapeHtml(text)

  // Bold+italic ***text***
  text = text.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
  // Bold **text**
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong style="color:#e2e8f0;font-weight:600">$1</strong>')
  // Italic *text* or _text_
  text = text.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em style="color:#a78bfa;font-style:italic">$1</em>')
  text = text.replace(/_(.+?)_/g, '<em style="color:#a78bfa;font-style:italic">$1</em>')
  // Inline code `text`
  text = text.replace(/`([^`]+)`/g, '<code style="background:rgba(167,139,250,0.1);color:#a78bfa;padding:1px 6px;border-radius:4px;font-family:monospace;font-size:0.85em;border:1px solid rgba(167,139,250,0.2)">$1</code>')
  // Links [text](url)
  text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label: string, url: string) => {
    const safeHref = sanitizeUrl(url)
    return `<a href="${safeHref}" style="color:#a78bfa;text-decoration:underline" target="_blank" rel="noopener noreferrer">${label}</a>`
  })
  return text
}

function sanitizeUrl(url: string): string {
  const normalized = url.trim().replace(/&amp;/g, '&')
  if (!normalized) return '#'

  // Allow only safe absolute schemes and safe relative links.
  if (
    normalized.startsWith('/') ||
    normalized.startsWith('#') ||
    normalized.startsWith('./') ||
    normalized.startsWith('../')
  ) {
    return escapeAttribute(normalized)
  }

  const lower = normalized.toLowerCase()
  if (lower.startsWith('https://') || lower.startsWith('http://') || lower.startsWith('mailto:')) {
    return escapeAttribute(normalized)
  }

  return '#'
}

function escapeAttribute(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}
