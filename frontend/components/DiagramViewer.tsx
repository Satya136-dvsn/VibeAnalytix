'use client'

import { useState } from 'react'
import MarkdownRenderer from './MarkdownRenderer'

type DiagramKey = 'dependency' | 'module' | 'class_diagram' | 'flow'

interface DiagramViewerProps {
  diagrams: Record<string, string>
}

const TAB_META: { key: DiagramKey; label: string; icon: string; description: string }[] = [
  {
    key: 'dependency',
    label: 'Dependency',
    icon: 'account_tree',
    description: 'File-level import dependency graph',
  },
  {
    key: 'module',
    label: 'Module Structure',
    icon: 'folder_open',
    description: 'Directory and module hierarchy',
  },
  {
    key: 'class_diagram',
    label: 'Class Diagram',
    icon: 'schema',
    description: 'Classes and methods extracted from AST',
  },
  {
    key: 'flow',
    label: 'Execution Flow',
    icon: 'route',
    description: 'Sequence diagram of entry points and cross-file calls',
  },
]

export default function DiagramViewer({ diagrams }: DiagramViewerProps) {
  const [activeTab, setActiveTab] = useState<DiagramKey>('dependency')

  const currentMeta = TAB_META.find(t => t.key === activeTab)!
  const mermaidSrc = diagrams[activeTab]

  // Wrap raw Mermaid string in a fenced code block for MarkdownRenderer
  const markdownContent = mermaidSrc
    ? '```mermaid\n' + mermaidSrc + '\n```'
    : '_No diagram data available for this view._'

  return (
    <div className="card-elevated flex flex-col overflow-hidden bg-surface-container-low border border-outline-variant/10">
      {/* Header */}
      <div className="px-6 py-4 border-b border-outline-variant/10 flex items-center justify-between bg-surface-container">
        <div className="flex items-center gap-3">
          <span
            className="material-symbols-outlined text-primary text-[22px]"
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            architecture
          </span>
          <div>
            <h2 className="font-headline text-on-surface text-lg">Architecture Diagrams</h2>
            <p className="text-[10px] uppercase tracking-widest text-on-surface-variant">
              Auto-generated · Zero API keys
            </p>
          </div>
        </div>
        <span className="chip text-[10px] bg-primary/10 border-primary/20 text-primary">
          Heuristic AST
        </span>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 px-4 pt-3 border-b border-outline-variant/10 bg-surface-container-low overflow-x-auto">
        {TAB_META.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-3 py-2 rounded-t-lg text-xs font-medium transition-all whitespace-nowrap
              ${
                activeTab === tab.key
                  ? 'text-primary border-b-2 border-primary bg-primary/5'
                  : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
              }`}
          >
            <span className="material-symbols-outlined text-[16px]">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Description bar */}
      <div className="px-6 py-2 bg-surface-container-lowest border-b border-outline-variant/5 flex items-center gap-2">
        <span className="material-symbols-outlined text-[14px] text-outline-variant">{currentMeta.icon}</span>
        <span className="text-[11px] text-on-surface-variant">{currentMeta.description}</span>
      </div>

      {/* Diagram content */}
      <div className="p-6 overflow-auto max-h-[70vh] min-h-[300px]">
        {mermaidSrc ? (
          <MarkdownRenderer content={markdownContent} />
        ) : (
          <div className="flex flex-col items-center justify-center h-48 text-on-surface-variant opacity-50 gap-3">
            <span className="material-symbols-outlined text-5xl text-outline-variant">data_object</span>
            <p className="text-sm">No {currentMeta.label.toLowerCase()} data generated yet.</p>
          </div>
        )}
      </div>
    </div>
  )
}
