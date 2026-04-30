/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
        dark: {
          50: '#18181b',
          100: '#27272a',
          200: '#3f3f46',
          300: '#52525b',
        }
      }
    },
  },
  plugins: [],
  darkMode: 'class',
}
