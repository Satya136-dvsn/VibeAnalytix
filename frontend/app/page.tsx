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
    <div className="va-landing min-h-screen text-slate-950 selection:bg-cyan-200 selection:text-slate-950">
      <div className="va-grid-overlay" aria-hidden="true" />

      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/85 backdrop-blur">
        <nav className="mx-auto flex h-20 w-full max-w-7xl items-center justify-between px-6 lg:px-10">
          <Link href="/" className="text-2xl font-headline font-semibold tracking-tight text-slate-950">
            VibeAnalytix
          </Link>

          <div className="hidden items-center gap-8 text-sm font-medium text-slate-600 md:flex">
            <a href="#platform" className="transition-colors hover:text-slate-950">Platform</a>
            <a href="#workflow" className="transition-colors hover:text-slate-950">Workflow</a>
            <a href="#security" className="transition-colors hover:text-slate-950">Security</a>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/sign-in-stitch"
              className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-100"
            >
              Sign in
            </Link>
            <Link
              href="/sign-up"
              className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-slate-900/20 transition-all hover:-translate-y-0.5 hover:bg-slate-800"
            >
              Start analysis
            </Link>
          </div>
        </nav>
      </header>

      <main>
        <section className="relative overflow-hidden border-b border-slate-200" id="platform">
          <div className="va-orb va-orb-one" aria-hidden="true" />
          <div className="va-orb va-orb-two" aria-hidden="true" />

          <div className="mx-auto grid w-full max-w-7xl gap-14 px-6 py-20 lg:grid-cols-2 lg:px-10 lg:py-28">
            <div className="va-fade-in-up space-y-8">
              <p className="inline-flex rounded-full border border-cyan-300/70 bg-cyan-100/80 px-4 py-1 text-xs font-bold uppercase tracking-[0.2em] text-cyan-800">
                Deliberate repository intelligence
              </p>
              <h1 className="font-headline text-5xl leading-tight tracking-tight text-slate-950 sm:text-6xl">
                Understand codebases before you change them.
              </h1>
              <p className="max-w-xl text-lg leading-relaxed text-slate-600">
                VibeAnalytix runs a structured pipeline across parsing, analysis, indexing, and explanation so your team can inspect architecture, dependencies, and behavior with confidence.
              </p>
              <div className="flex flex-col gap-4 sm:flex-row">
                <Link
                  href="/sign-up"
                  className="inline-flex items-center justify-center rounded-xl bg-slate-950 px-7 py-3.5 text-sm font-semibold text-white transition-all hover:-translate-y-0.5 hover:bg-slate-800"
                >
                  Create workspace
                </Link>
                <Link
                  href="/dashboard"
                  className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-7 py-3.5 text-sm font-semibold text-slate-800 transition-colors hover:bg-slate-100"
                >
                  Open dashboard
                </Link>
              </div>
            </div>

            <aside className="va-fade-in-up-delay rounded-2xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-900/5">
              <div className="mb-4 flex items-center justify-between border-b border-slate-100 pb-3">
                <h2 className="text-sm font-bold uppercase tracking-[0.16em] text-slate-500">Pipeline preview</h2>
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">Active</span>
              </div>

              <div className="space-y-4">
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Input</p>
                  <p className="mt-1 text-sm font-medium text-slate-800">Repository URL and branch</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Execution path</p>
                  <p className="mt-1 text-sm leading-relaxed text-slate-700">
                    ingestion.py → parser.py → analysis.py → knowledge_builder.py → query_service.py
                  </p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Output</p>
                  <p className="mt-1 text-sm font-medium text-slate-800">Grounded technical explanations with source-backed context</p>
                </div>
              </div>
            </aside>
          </div>
        </section>

        <section className="border-b border-slate-200 bg-white py-20" id="workflow">
          <div className="mx-auto w-full max-w-7xl px-6 lg:px-10">
            <div className="mb-12 max-w-2xl">
              <h2 className="font-headline text-4xl leading-tight text-slate-950">A workflow built for engineering teams</h2>
              <p className="mt-4 text-lg text-slate-600">
                Each stage is explicit and inspectable. No hidden mock responses, no synthetic output pipelines.
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {workflow.map((item) => (
                <article key={item.step} className="rounded-2xl border border-slate-200 bg-slate-50 p-6">
                  <p className="text-sm font-bold tracking-wide text-cyan-700">{item.step}</p>
                  <h3 className="mt-2 text-xl font-semibold text-slate-900">{item.title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-slate-600">{item.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="border-b border-slate-200 bg-slate-50 py-20">
          <div className="mx-auto w-full max-w-7xl px-6 lg:px-10">
            <div className="mb-12 flex flex-wrap items-end justify-between gap-6">
              <div className="max-w-2xl">
                <h2 className="font-headline text-4xl leading-tight text-slate-950">Real platform capabilities</h2>
                <p className="mt-4 text-lg text-slate-600">
                  These are directly mapped to the current backend modules powering analysis in this repository.
                </p>
              </div>
              <Link href="/jobs" className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100">
                View jobs
              </Link>
            </div>

            <div className="grid gap-5 md:grid-cols-2">
              {platformCapabilities.map((capability) => (
                <article key={capability.title} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                  <h3 className="text-xl font-semibold text-slate-900">{capability.title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-slate-600">{capability.detail}</p>
                  <p className="mt-4 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{capability.file}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="bg-white py-20" id="security">
          <div className="mx-auto w-full max-w-7xl px-6 lg:px-10">
            <div className="grid gap-8 rounded-3xl border border-slate-200 bg-gradient-to-r from-cyan-50 via-white to-amber-50 p-8 lg:grid-cols-3 lg:p-10">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-700">Security and operations</p>
                <h2 className="mt-4 font-headline text-4xl leading-tight text-slate-950">Built for controlled analysis</h2>
              </div>
              <article className="rounded-2xl border border-slate-200 bg-white p-5">
                <h3 className="text-lg font-semibold text-slate-900">Read-only ingestion</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">
                  Repository ingestion is designed for analysis only. The pipeline focuses on extracting structure and context, not modifying source.
                </p>
              </article>
              <article className="rounded-2xl border border-slate-200 bg-white p-5">
                <h3 className="text-lg font-semibold text-slate-900">Job-level traceability</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">
                  Jobs, statuses, and progress are exposed through backend routes for clear operational visibility.
                </p>
              </article>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-7xl flex-col items-start justify-between gap-6 px-6 py-10 text-sm text-slate-500 md:flex-row md:items-center lg:px-10">
          <p>VibeAnalytix</p>
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
