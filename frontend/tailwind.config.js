/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Identité Tier Fist : violet électrique + fond ardoise profond.
        brand: {
          50: '#f4f1ff',
          100: '#e9e3ff',
          200: '#d4c8ff',
          300: '#b6a1ff',
          400: '#9370ff',
          500: '#7a45f5',
          600: '#6a29e0',
          700: '#5a1fbb',
          800: '#4a1c97',
          900: '#3d1a7a',
          950: '#241046',
        },
        // Couleurs de rang figées par la spec (§13), non personnalisables.
        rank: {
          red: '#ef4444',
          orange: '#f97316',
          yellow: '#eab308',
          green: '#22c55e',
          blue: '#3b82f6',
        },
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', 'system-ui', 'sans-serif'],
      },
      keyframes: {
        'pop-in': {
          '0%': { opacity: '0', transform: 'translateY(6px) scale(0.98)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        wiggle: {
          '0%, 100%': { transform: 'rotate(-2deg)' },
          '50%': { transform: 'rotate(2deg)' },
        },
      },
      animation: {
        'pop-in': 'pop-in 0.2s ease-out',
        wiggle: 'wiggle 2.5s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
