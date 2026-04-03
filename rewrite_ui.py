import os

fp = r"c:\VibeAnalytix\frontend\app\jobs\[id]\page.tsx"
with open(fp, "r", encoding="utf-8") as f:
    code = f.read()

replacements = {
    '"min-h-screen bg-slate-50"': '"min-h-screen bg-[#05050A] text-slate-200"',
    '"bg-white border-b border-slate-200 sticky top-0 z-10"': '"bg-[#0A0A0F]/80 backdrop-blur-xl border-b border-purple-500/20 sticky top-0 z-10 shadow-[0_4px_30px_rgba(168,85,247,0.15)]"',
    'text-indigo-600 overflow-y-auto': 'text-purple-400 overflow-y-auto',
    'text-indigo-600 hover:text-indigo-700': 'text-fuchsia-400 hover:text-purple-300 transition-colors',
    'bg-green-100 text-green-800': 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-[0_0_10px_rgba(16,185,129,0.2)]',
    'bg-red-100 text-red-800': 'bg-rose-500/10 text-rose-400 border border-rose-500/20 shadow-[0_0_10px_rgba(244,63,94,0.2)]',
    'bg-blue-100 text-blue-800': 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 shadow-[0_0_10px_rgba(6,182,212,0.2)]',
    'bg-red-100 border border-red-300 rounded-lg text-red-800': 'bg-rose-950/40 border border-rose-900/50 rounded-lg text-rose-300 shadow-[0_0_15px_rgba(225,29,72,0.15)]',
    'bg-red-50 border border-red-200': 'bg-rose-950/20 border border-rose-900/30',
    'text-red-900': 'text-rose-400',
    'text-red-800': 'text-rose-300',
    'bg-blue-50 border border-blue-200': 'bg-fuchsia-950/20 border border-fuchsia-900/30',
    'text-blue-900': 'text-fuchsia-400',
    'text-blue-800': 'text-fuchsia-300',
    'bg-blue-200': 'bg-[#1A1A24]',
    'bg-blue-600': 'bg-gradient-to-r from-fuchsia-500 to-purple-600 shadow-[0_0_15px_rgba(217,70,239,0.5)]',
    'card p-8': 'bg-[#0A0A0F] border border-purple-500/20 rounded-2xl shadow-[0_8px_32px_rgba(168,85,247,0.1)] p-8 backdrop-blur-md',
    'card overflow-y-auto': 'bg-[#0A0A0F] border border-purple-500/20 rounded-2xl shadow-[0_8px_32px_rgba(168,85,247,0.1)] overflow-y-auto backdrop-blur-md',
    'border-transparent text-slate-600 hover:text-slate-900': 'border-transparent text-slate-400 hover:text-purple-300',
    'border-indigo-600 text-indigo-600': 'border-fuchsia-500 text-fuchsia-400 shadow-[0_2px_15px_rgba(217,70,239,0.25)]',
    'bg-indigo-100 text-indigo-800': 'bg-purple-500/10 text-purple-300 border border-purple-500/20 shadow-[0_0_10px_rgba(168,85,247,0.2)]',
    'hover:bg-indigo-50': 'hover:bg-purple-500/10 hover:shadow-[0_0_10px_rgba(168,85,247,0.1)]',
    'text-slate-900': 'text-white',
    'text-slate-800': 'text-slate-200',
    'text-slate-700': 'text-slate-300',
    'text-slate-600': 'text-slate-400',
    'text-slate-500': 'text-slate-500',
    'bg-indigo-100 text-indigo-700': 'bg-purple-500/20 text-purple-300 border-l-2 border-purple-400',
    'hover:bg-slate-100': 'hover:bg-white/5',
    'text-indigo-500': 'text-fuchsia-400 drop-shadow-[0_0_8px_rgba(232,121,249,0.5)]',
    'border border-indigo-200': 'border border-purple-500/20',
    'bg-indigo-50': 'bg-purple-500/5',
    'text-indigo-800': 'text-purple-300',
    'text-indigo-700': 'text-fuchsia-400',
    'text-indigo-600': 'text-fuchsia-500',
    'bg-amber-50 border border-amber-200': 'bg-amber-950/20 border border-amber-900/30',
    'text-amber-800': 'text-amber-400',
    'text-amber-700': 'text-amber-300',
    'border-slate-200': 'border-white/10',
}

for k, v in replacements.items():
    code = code.replace(k, v)

with open(fp, "w", encoding="utf-8") as f:
    f.write(code)
print("done")
