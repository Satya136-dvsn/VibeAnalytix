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
        'primary':                '#b6a0ff',
        'primary-dim':            '#7e51ff',
        'primary-fixed':          '#a98fff',
        'primary-fixed-dim':      '#9c7eff',
        'primary-container':      '#a98fff',
        'on-primary':             '#340090',
        'on-primary-fixed':       '#000000',
        'on-primary-fixed-variant':'#32008a',
        'on-primary-container':   '#280072',
        'inverse-primary':        '#6834eb',

        'secondary':              '#d7e4ec',
        'secondary-dim':          '#c9d6de',
        'secondary-fixed':        '#d7e4ec',
        'secondary-fixed-dim':    '#c9d6de',
        'secondary-container':    '#3c494f',
        'on-secondary':           '#47545a',
        'on-secondary-fixed':     '#354147',
        'on-secondary-fixed-variant':'#515d64',
        'on-secondary-container': '#c5d2da',

        'tertiary':               '#81ecff',
        'tertiary-dim':           '#00d4ec',
        'tertiary-fixed':         '#00e3fd',
        'tertiary-fixed-dim':     '#00d4ec',
        'tertiary-container':     '#00e3fd',
        'on-tertiary':            '#005762',
        'on-tertiary-fixed':      '#003840',
        'on-tertiary-fixed-variant':'#005762',
        'on-tertiary-container':  '#004d57',

        'surface':                '#0d0e10',
        'surface-dim':            '#0d0e10',
        'surface-bright':         '#2b2c2f',
        'surface-variant':        '#242629',
        'surface-container-lowest':'#000000',
        'surface-container-low':  '#121316',
        'surface-container':      '#181a1c',
        'surface-container-high': '#1e2022',
        'surface-container-highest':'#242629',
        'surface-tint':           '#b6a0ff',
        'on-surface':             '#fdfbfe',
        'on-surface-variant':     '#ababad',
        'inverse-surface':        '#faf9fb',
        'inverse-on-surface':     '#555557',

        'background':             '#0d0e10',
        'on-background':          '#fdfbfe',

        'outline':                '#757578',
        'outline-variant':        '#47484a',

        'error':                  '#ff6e84',
        'error-dim':              '#d73357',
        'error-container':        '#a70138',
        'on-error':               '#490013',
        'on-error-container':     '#ffb2b9',
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
  plugins: [],
}
