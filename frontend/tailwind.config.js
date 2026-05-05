/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './pages/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // ── Primary (indigo/violet) ──────────────────────────────
        'primary':                     '#4f46e5',
        'primary-dim':                 '#4338ca',
        'primary-fixed':               '#e0e7ff',
        'primary-fixed-dim':           '#c7d2fe',
        'primary-container':           '#e0e7ff',
        'on-primary':                  '#ffffff',
        'on-primary-fixed':            '#1e1b4b',
        'on-primary-fixed-variant':    '#3730a3',
        'on-primary-container':        '#1e1b4b',
        'inverse-primary':             '#818cf8',

        // ── Secondary (slate) ────────────────────────────────────
        'secondary':                   '#64748b',
        'secondary-dim':               '#475569',
        'secondary-fixed':             '#f1f5f9',
        'secondary-fixed-dim':         '#e2e8f0',
        'secondary-container':         '#f1f5f9',
        'on-secondary':                '#ffffff',
        'on-secondary-fixed':          '#0f172a',
        'on-secondary-fixed-variant':  '#334155',
        'on-secondary-container':      '#334155',

        // ── Tertiary (cyan) ──────────────────────────────────────
        'tertiary':                    '#0891b2',
        'tertiary-dim':                '#0e7490',
        'tertiary-fixed':              '#cffafe',
        'tertiary-fixed-dim':          '#a5f3fc',
        'tertiary-container':          '#cffafe',
        'on-tertiary':                 '#ffffff',
        'on-tertiary-fixed':           '#083344',
        'on-tertiary-fixed-variant':   '#155e75',
        'on-tertiary-container':       '#155e75',

        // ── Surface (white / light-gray) ─────────────────────────
        'surface':                     '#ffffff',
        'surface-dim':                 '#f1f5f9',
        'surface-bright':              '#ffffff',
        'surface-variant':             '#e2e8f0',
        'surface-container-lowest':    '#ffffff',
        'surface-container-low':       '#f8fafc',
        'surface-container':           '#f1f5f9',
        'surface-container-high':      '#e2e8f0',
        'surface-container-highest':   '#cbd5e1',
        'surface-tint':                '#4f46e5',
        'on-surface':                  '#0f172a',
        'on-surface-variant':          '#475569',
        'inverse-surface':             '#1e293b',
        'inverse-on-surface':          '#f8fafc',

        // ── Background ───────────────────────────────────────────
        'background':                  '#f8fafc',
        'on-background':               '#0f172a',

        // ── Outline ──────────────────────────────────────────────
        'outline':                     '#94a3b8',
        'outline-variant':             '#e2e8f0',

        // ── Error ────────────────────────────────────────────────
        'error':                       '#dc2626',
        'error-dim':                   '#ef4444',
        'error-container':             '#fee2e2',
        'on-error':                    '#ffffff',
        'on-error-container':          '#7f1d1d',
      },
      fontFamily: {
        headline: ['Newsreader', 'Georgia', 'serif'],
        body:     ['Inter', 'sans-serif'],
        label:    ['Inter', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '0.125rem',
        lg:      '0.25rem',
        xl:      '0.5rem',
        full:    '0.75rem',
        '2xl':   '1rem',
      },
      keyframes: {
        fadeUp: {
          '0%':   { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        glow: {
          '0%, 100%': { opacity: '0.6' },
          '50%':      { opacity: '1' },
        },
      },
      animation: {
        'fade-up': 'fadeUp 0.5s ease both',
        'glow':    'glow 2s ease-in-out infinite',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/container-queries')
  ],
}
