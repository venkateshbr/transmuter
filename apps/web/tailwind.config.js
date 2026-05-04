/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{html,ts}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Libre Franklin', 'Franklin Gothic Medium', 'Arial Narrow', 'Arial', 'sans-serif'],
      },
      colors: {
        brand: {
          primary:  '#071f3c',
          hover:    '#063962',
          light:    '#63a9d8',
          muted:    '#d7e8f3',
          subtle:   '#f4f6f8',
          accent:   '#0c4f86',
          success:  '#166534',
          warning:  '#b7791f',
          danger:   '#b42318',
        },
      },
    },
  },
  plugins: [],
};
