/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        accent: {
          50: '#f7efd7',
          100: '#eedca0',
          500: '#d4af37',
          600: '#c39a20',
          700: '#b8860b',
        },
        surface: {
          DEFAULT: '#141414',
          subtle: '#1a1a1a',
          muted: '#222222',
        },
        border: '#2d2a24',
      },
      boxShadow: {
        'premium-sm': '0 2px 8px rgba(0,0,0,0.28)',
        'premium-md': '0 6px 18px rgba(0,0,0,0.34)',
        'premium-lg': '0 12px 28px rgba(0,0,0,0.42)',
        'premium-hover': '0 20px 32px rgba(0,0,0,0.5)',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-in': 'slideIn 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(0)' },
        },
      },
    },
  },
  plugins: [],
}
