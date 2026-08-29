/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
  theme: {
    extend: {
      fontFamily: {
        serif: ['Spectral', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      colors: {
        paper: '#F4F3EE',
        panel: '#FFFFFF',
        navy: {
          DEFAULT: '#1A365D',
          light: '#26497E',
          dark: '#122744',
        },
        stamp: {
          DEFAULT: '#C05621',
          dark: '#9C4419',
        },
        pass: { bg: '#E6F4EA', text: '#1E4620', border: '#A8D5B2' },
        fail: { bg: '#FCE8E6', text: '#A50E0E', border: '#F5B7B1' },
        review: { bg: '#FEF7E0', text: '#8B5A00', border: '#FAD7A1' },
        ink: { DEFAULT: '#111827', muted: '#4B5563', faint: '#9CA3AF' },
        line: '#D1D5DB',
        divider: '#E5E7EB',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: { DEFAULT: 'hsl(var(--card))', foreground: 'hsl(var(--card-foreground))' },
        popover: { DEFAULT: 'hsl(var(--popover))', foreground: 'hsl(var(--popover-foreground))' },
        primary: { DEFAULT: 'hsl(var(--primary))', foreground: 'hsl(var(--primary-foreground))' },
        secondary: { DEFAULT: 'hsl(var(--secondary))', foreground: 'hsl(var(--secondary-foreground))' },
        muted: { DEFAULT: 'hsl(var(--muted))', foreground: 'hsl(var(--muted-foreground))' },
        accent: { DEFAULT: 'hsl(var(--accent))', foreground: 'hsl(var(--accent-foreground))' },
        destructive: { DEFAULT: 'hsl(var(--destructive))', foreground: 'hsl(var(--destructive-foreground))' },
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      keyframes: {
        'accordion-down': { from: { height: '0' }, to: { height: 'var(--radix-accordion-content-height)' } },
        'accordion-up': { from: { height: 'var(--radix-accordion-content-height)' }, to: { height: '0' } },
        'fade-up': { from: { opacity: '0', transform: 'translateY(8px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        'stamp-in': { '0%': { opacity: '0', transform: 'scale(1.4) rotate(-8deg)' }, '60%': { opacity: '1', transform: 'scale(0.96) rotate(-5deg)' }, '100%': { opacity: '0.92', transform: 'scale(1) rotate(-4deg)' } },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'fade-up': 'fade-up 0.35s ease-out both',
        'stamp-in': 'stamp-in 0.5s cubic-bezier(0.2,0.8,0.2,1) both',
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
