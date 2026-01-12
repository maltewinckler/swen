/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Background layers
        'bg-base': '#0a0a0b',
        'bg-surface': '#121214',
        'bg-elevated': '#1a1a1d',
        'bg-hover': '#232326',

        // Borders
        'border-subtle': '#27272a',
        'border-default': '#3f3f46',
        'border-focus': '#52525b',

        // Text
        'text-primary': '#fafafa',
        'text-secondary': '#a1a1aa',
        'text-muted': '#71717a',
        'text-disabled': '#52525b',

        // Accent colors
        'accent-primary': '#3b82f6',
        'accent-success': '#22c55e',
        'accent-danger': '#ef4444',
        'accent-warning': '#f59e0b',
        'accent-info': '#06b6d4',

        // Chart colors
        'chart-1': '#8b5cf6',
        'chart-2': '#ec4899',
        'chart-3': '#14b8a6',
        'chart-4': '#f97316',
        'chart-5': '#84cc16',
      },
      fontFamily: {
        sans: ['Inter', 'SF Pro Display', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        'display': ['2.25rem', { lineHeight: '2.5rem', fontWeight: '600' }],
        'tiny': ['0.6875rem', { lineHeight: '1rem', fontWeight: '500' }],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
      },
      boxShadow: {
        'glow': '0 0 20px rgba(59, 130, 246, 0.15)',
        'glow-success': '0 0 20px rgba(34, 197, 94, 0.15)',
        'glow-danger': '0 0 20px rgba(239, 68, 68, 0.15)',
      },
      transitionDuration: {
        'fast': '150ms',
        'normal': '250ms',
        'slow': '400ms',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
