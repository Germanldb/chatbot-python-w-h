module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#FFFFFF',
        foreground: '#0F172A',
        card: '#FFFFFF',
        'card-foreground': '#0F172A',
        popover: '#FFFFFF',
        'popover-foreground': '#0F172A',
        primary: '#044736',
        'primary-foreground': '#FFFFFF',
        secondary: '#F1F5F9',
        'secondary-foreground': '#0F172A',
        muted: '#F8FAFC',
        'muted-foreground': '#64748B',
        accent: '#D4FF33',
        'accent-foreground': '#044736',
        destructive: '#EF4444',
        'destructive-foreground': '#FFFFFF',
        border: '#E2E8F0',
        input: '#E2E8F0',
        ring: '#044736',
      },
      fontFamily: {
        heading: ['Manrope', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [
    require('tailwindcss-animate'),
  ],
}