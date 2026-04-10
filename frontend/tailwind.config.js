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
          50: '#f5f5ed',
          100: '#e7e7d6',
          200: '#cfd0ae',
          300: '#b2b582',
          400: '#949b5f',
          500: '#7a8246',
          600: '#666d3c',
          700: '#525830',
          800: '#434927',
          900: '#383d22',
          950: '#1f2214',
        },
        surface: {
          50: '#f8f6f2',
          100: '#efeae1',
          200: '#dfd7ca',
          300: '#c8bdab',
          400: '#a99b86',
          500: '#877a66',
          600: '#6b5f50',
          700: '#564c40',
          800: '#463d33',
          900: '#2f2a24',
          950: '#1c1916',
        },
      },
      fontFamily: {
        sans: ['Public Sans', 'Segoe UI', 'system-ui', 'sans-serif'],
        display: ['Fraunces', 'Georgia', 'serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.6s ease-out forwards',
        'slide-up': 'slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'float': 'float 8s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(24px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-12px)' },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
