'use client'

import React from 'react'
import Link from 'next/link'

export default function LandingPage() {
  const platformCapabilities = [
    {
      title: 'Language-aware parsing',
      detail:
        'Tree-sitter parsing builds structured syntax trees before any explanation is generated.',
      file: 'backend/app/parser.py',
    },
    {
      title: 'Multi-pass repository analysis',
      detail:
        'Passes for structure, semantics, and cross-file relationships are executed in sequence.',
      file: 'backend/app/analysis.py',
    },
    {
      title: 'Hierarchical knowledge synthesis',
      detail:
        'Function, file, module, and project summaries are built and stored for grounded answers.',
      file: 'backend/app/knowledge_builder.py',
    },
    {
      title: 'Vector retrieval pipeline',
      detail:
        'Embeddings and pgvector-backed search retrieve relevant context for every query.',
      file: 'backend/app/vector_store.py',
    },
  ]

  const workflow = [
    {
      step: '01',
      title: 'Ingest',
      text: 'Connect a repository and create an analysis job through the jobs API.',
    },
    {
      step: '02',
      title: 'Analyze',
      text: 'Run parser and analysis passes to construct a durable repository model.',
    },
    {
      step: '03',
      title: 'Index',
      text: 'Generate embeddings and knowledge summaries for precise retrieval.',
    },
    {
      step: '04',
      title: 'Explain',
      text: 'Answer engineering questions with citations and repository-grounded context.',
    },
  ]

  return (
    <div className="va-landing relative min-h-screen flex flex-col selection:bg-cyan-200 selection:text-slate-950 overflow-hidden">
      <div className="va-grid-overlay" aria-hidden="true" />
      
      <header className="relative z-20 border-b border-slate-200/60 bg-white/75 backdrop-blur-xl transition-all duration-300">
        <nav className="mx-auto flex h-20 w-full max-w-7xl items-center justify-between px-6 lg:px-10">
          <Link href="/" className="text-2xl font-headline font-semibold tracking-tight text-slate-950 flex items-center gap-2 group hover:text-cyan-700 transition-colors duration-200">
            <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-600 to-cyan-500 flex items-center justify-center shadow-md shadow-cyan-600/30 group-hover:shadow-lg group-hover:shadow-cyan-600/40 transition-all duration-300">
              <span className="text-white text-lg font-bold leading-none">V</span>
            </span>
            VibeAnalytix
          </Link>

          <div className="hidden items-center gap-8 text-sm font-medium text-slate-600 md:flex">
            <a href="#platform" className="transition-all duration-200 hover:text-slate-900 hover:text-base relative after:absolute after:bottom-0 after:left-0 after:w-0 after:h-0.5 after:bg-gradient-to-r after:from-cyan-600 after:to-cyan-500 after:transition-all after:duration-300 hover:after:w-full">Platform</a>
            <a href="#workflow" className="transition-all duration-200 hover:text-slate-900 hover:text-base relative after:absolute after:bottom-0 after:left-0 after:w-0 after:h-0.5 after:bg-gradient-to-r after:from-cyan-600 after:to-cyan-500 after:transition-all after:duration-300 hover:after:w-full">Workflow</a>
            <a href="#security" className="transition-all duration-200 hover:text-slate-900 hover:text-base relative after:absolute after:bottom-0 after:left-0 after:w-0 after:h-0.5 after:bg-gradient-to-r after:from-cyan-600 after:to-cyan-500 after:transition-all after:duration-300 hover:after:w-full">Security</a>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/auth"
              className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-600 transition-all duration-200 hover:bg-slate-100 hover:text-slate-900 hover:backdrop-blur-md group"
            >
              Sign in
            </Link>
            <Link
              href="/sign-up"
              className="rounded-lg bg-gradient-to-r from-cyan-600 to-cyan-500 px-5 py-2 text-sm font-semibold text-white shadow-md shadow-cyan-600/30 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-cyan-600/40 active:scale-95"
            >
              Start analysis
            </Link>
          </div>
        </nav>
      </header>

      <main className="relative z-10">
        <section className="relative overflow-hidden border-b border-slate-200/60" id="platform">
          <div className="mx-auto grid w-full max-w-7xl gap-14 px-6 py-20 lg:grid-cols-2 lg:px-10 lg:py-28">
            <div className="va-fade-in-up space-y-8 relative z-10">
              <p className="inline-flex rounded-full border border-cyan-300/60 bg-cyan-100/80 px-4 py-1 text-xs font-bold uppercase tracking-[0.2em] text-cyan-800 shadow-md shadow-cyan-300/20 hover:shadow-lg hover:shadow-cyan-400/30 transition-all duration-200">
                Deliberate repository intelligence
              </p>
              <h1 className="font-headline text-5xl leading-tight tracking-tight text-slate-950 sm:text-7xl hover:text-transparent hover:bg-clip-text hover:bg-gradient-to-r hover:from-cyan-700 hover:to-cyan-600 transition-all duration-300">
                Understand codebases <span className="italic text-cyan-700">before you change them.</span>
              </h1>
              <p className="max-w-xl text-lg leading-relaxed text-slate-600 transition-all duration-300 hover:text-slate-700">
                VibeAnalytix runs a structured pipeline across parsing, analysis, indexing, and explanation so your team can inspect architecture, dependencies, and behavior with confidence.
              </p>
              <div className="flex flex-col gap-4 sm:flex-row">
                <Link
                  href="/sign-up"
                  className="inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-cyan-600 to-cyan-500 px-7 py-3.5 text-sm font-semibold text-white transition-all duration-300 hover:-translate-y-1 hover:scale-105 shadow-md shadow-cyan-600/30 hover:shadow-lg hover:shadow-cyan-600/40 active:scale-95"
                >
                  Create workspace
                </Link>
                <Link
                  href="/dashboard"
                  className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-7 py-3.5 text-sm font-semibold text-slate-900 shadow-sm transition-all duration-300 hover:bg-slate-50 hover:border-slate-400 hover:shadow-md hover:shadow-slate-300/20 active:scale-95"
                >
                  Open dashboard
                </Link>
              </div>
            </div>

            <aside className="va-fade-in-up-delay relative z-10 rounded-2xl border border-slate-300/60 bg-white/95 p-6 shadow-lg shadow-slate-300/20 hover:border-slate-400 hover:bg-white hover:shadow-xl hover:shadow-slate-300/30 transition-all duration-500">
              <div className="mb-4 flex items-center justify-between border-b border-slate-200 pb-3">
                <h2 className="text-sm font-bold uppercase tracking-[0.16em] text-slate-600">Pipeline preview</h2>
                <span className="rounded-full border border-emerald-400/70 bg-emerald-100/80 px-3 py-1 text-xs font-semibold text-emerald-800 shadow-sm shadow-emerald-300/30 animate-pulse">Active</span>
              </div>

              <div className="space-y-4">
                <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 transition-all duration-300 hover:bg-slate-100 hover:border-slate-300 hover:shadow-md hover:shadow-slate-200/50">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Input</p>
                  <p className="mt-1 text-sm font-medium text-slate-700">Repository URL and branch</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 transition-all duration-300 hover:bg-slate-100 hover:border-slate-300 hover:shadow-md hover:shadow-slate-200/50">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Execution path</p>
                  <p className="mt-1 text-sm leading-relaxed text-slate-700 font-mono text-[13px]">
                    <span className="text-cyan-700">ingestion.py</span> → <span className="text-cyan-600">parser.py</span> → analysis.py → knowledge_builder.py → query_service.py
                  </p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 transition-all duration-300 hover:bg-slate-100 hover:border-slate-300 hover:shadow-md hover:shadow-slate-200/50">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Output</p>
                  <p className="mt-1 text-sm font-medium text-slate-700">Grounded technical explanations with source-backed context</p>
                </div>
              </div>
            </aside>
          </div>
        </section>

        <section className="relative border-b border-slate-200/60 py-20" id="workflow">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full max-w-4xl bg-cyan-300/10 blur-[100px] rounded-full pointer-events-none" />
          <div className="mx-auto w-full max-w-7xl px-6 lg:px-10 relative z-10">
            <div className="mb-12 max-w-2xl">
              <h2 className="font-headline text-4xl leading-tight text-slate-950 hover:text-transparent hover:bg-clip-text hover:bg-gradient-to-r hover:from-cyan-700 hover:to-cyan-600 transition-all duration-300">A workflow built for engineering teams</h2>
              <p className="mt-4 text-lg text-slate-600 hover:text-slate-700 transition-colors duration-200">
                Each stage is explicit and inspectable. No hidden mock responses, no synthetic output pipelines.
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {workflow.map((item, idx) => (
                <article key={item.step} className="group rounded-2xl border border-slate-300/60 bg-white/80 p-6 shadow-sm transition-all duration-300 hover:border-cyan-400/70 hover:bg-white hover:shadow-lg hover:shadow-cyan-300/20 hover:-translate-y-2" style={{ animationDelay: `${idx * 100}ms` }}>
                  <p className="text-sm font-bold tracking-wide text-cyan-700 group-hover:text-cyan-600 transition-colors duration-300">{item.step}</p>
                  <h3 className="mt-2 text-xl font-semibold text-slate-900 group-hover:text-cyan-700 transition-colors duration-300">{item.title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-slate-600 group-hover:text-slate-700 transition-colors duration-300">{item.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="relative border-b border-slate-200/60 py-20">
          <div className="mx-auto w-full max-w-7xl px-6 lg:px-10 relative z-10">
            <div className="mb-12 flex flex-wrap items-end justify-between gap-6">
              <div className="max-w-2xl">
                <h2 className="font-headline text-4xl leading-tight text-slate-950 hover:text-transparent hover:bg-clip-text hover:bg-gradient-to-r hover:from-cyan-700 hover:to-cyan-600 transition-all duration-300">Real platform capabilities</h2>
                <p className="mt-4 text-lg text-slate-600 hover:text-slate-700 transition-colors duration-200">
                  These are directly mapped to the current backend modules powering analysis in this repository.
                </p>
              </div>
              <Link href="/jobs" className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition-all hover:bg-slate-50 hover:border-slate-400 hover:shadow-md hover:shadow-slate-300/20 active:scale-95">
                View jobs
              </Link>
            </div>

            <div className="grid gap-5 md:grid-cols-2">
              {platformCapabilities.map((capability, idx) => (
                <article key={capability.title} className="group rounded-2xl border border-slate-300/60 bg-white/80 p-6 shadow-sm transition-all duration-300 hover:border-cyan-400/70 hover:bg-white hover:shadow-lg hover:shadow-cyan-300/20 hover:-translate-y-2" style={{ animationDelay: `${idx * 75}ms` }}>
                  <h3 className="text-xl font-semibold text-slate-900 group-hover:text-cyan-700 transition-colors duration-300">{capability.title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-slate-600 group-hover:text-slate-700 transition-colors duration-300">{capability.detail}</p>
                  <p className="mt-4 text-xs font-semibold uppercase tracking-[0.12em] text-cyan-700 group-hover:text-cyan-600 transition-colors duration-300">{capability.file}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="relative py-20" id="security">
          <div className="absolute bottom-0 right-0 w-[50%] h-[50%] rounded-full bg-cyan-300/10 blur-[120px] pointer-events-none" />
          <div className="mx-auto w-full max-w-7xl px-6 lg:px-10 relative z-10">
            <div className="grid gap-8 rounded-3xl border border-slate-300/60 bg-white/80 p-8 lg:grid-cols-3 lg:p-10 shadow-lg shadow-slate-300/20">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-700">Security and operations</p>
                <h2 className="mt-4 font-headline text-4xl leading-tight text-slate-950 hover:text-transparent hover:bg-clip-text hover:bg-gradient-to-r hover:from-cyan-700 hover:to-cyan-600 transition-all duration-300">Built for controlled analysis</h2>
              </div>
              <article className="rounded-2xl border border-slate-300/60 bg-slate-50/80 p-5 shadow-sm hover:shadow-md hover:shadow-cyan-300/20 transition-all duration-300">
                <h3 className="text-lg font-semibold text-slate-900">Read-only ingestion</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600 hover:text-slate-700 transition-colors duration-200">
                  Repository ingestion is designed for analysis only. The pipeline focuses on extracting structure and context, not modifying source.
                </p>
              </article>
              <article className="rounded-2xl border border-slate-300/60 bg-slate-50/80 p-5 shadow-sm hover:shadow-md hover:shadow-cyan-300/20 transition-all duration-300">
                <h3 className="text-lg font-semibold text-slate-900">Job-level traceability</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600 hover:text-slate-700 transition-colors duration-200">
                  Jobs, statuses, and progress are exposed through backend routes for clear operational visibility.
                </p>
              </article>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200/60 relative z-10 bg-white/50">
        <div className="mx-auto flex w-full max-w-7xl flex-col items-start justify-between gap-6 px-6 py-10 text-sm text-slate-600 md:flex-row md:items-center lg:px-10">
          <p className="flex items-center gap-2 font-semibold text-slate-900">
            <span className="w-5 h-5 rounded-[4px] bg-gradient-to-br from-cyan-600 to-cyan-500 flex items-center justify-center">
              <span className="text-white text-[10px] font-bold leading-none">V</span>
            </span>
            VibeAnalytix
          </p>
          <div className="flex gap-6">
            <Link href="/sign-up" className="transition-colors hover:text-slate-900">Get started</Link>
            <Link href="/dashboard" className="transition-colors hover:text-slate-900">Dashboard</Link>
            <Link href="/settings" className="transition-colors hover:text-slate-900">Settings</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
