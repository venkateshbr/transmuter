/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{html,ts}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      colors: {
        brand: {
          primary:  '#7c3aed',
          hover:    '#6d28d9',
          light:    '#a78bfa',
          muted:    '#ede9fe',
          subtle:   '#f5f3ff',
          accent:   '#a855f7',
          success:  '#10b981',
          warning:  '#f59e0b',
          danger:   '#ef4444',
        },
      },
    },
  },
  plugins: [],
};
