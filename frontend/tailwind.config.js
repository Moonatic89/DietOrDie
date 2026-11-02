/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        fantasy: {
          dark: '#0f172a',
          gold: '#f59e0b',
          crimson: '#dc2626',
          emerald: '#10b981',
          slate: '#1e293b'
        }
      }
    },
  },
  plugins: [],
}
