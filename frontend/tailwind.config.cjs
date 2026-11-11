
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          blue: "#1D4ED8",
          teal: "#0D9488",
          indigo: "#4F46E5",
        },
      },
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "Roboto",
          '"Helvetica Neue"',
          "Arial",
          "sans-serif",
        ],
        devanagari: [
          '"Noto Sans Devanagari"',
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [
    require("daisyui"),
  ],
  daisyui: {
    themes: [
      {
        sandeshvani: {
          "primary": "#1D4ED8",
          "primary-content": "#FFFFFF",
          "secondary": "#0D9488",
          "secondary-content": "#FFFFFF",
          "accent": "#4F46E5",
          "accent-content": "#FFFFFF",
          "neutral": "#334155",
          "neutral-content": "#F8FAFC",
          "base-100": "#FFFFFF",
          "base-200": "#F8FAFC",
          "base-300": "#F1F5F9",
          "base-content": "#0F172A",
          "info": "#0369A1",
          "info-content": "#FFFFFF",
          "success": "#15803D",
          "success-content": "#FFFFFF",
          "warning": "#B45309",
          "warning-content": "#FFFFFF",
          "error": "#B91C1C",
          "error-content": "#FFFFFF",
        },
      },
      "light",
    ],
    darkTheme: false,
    base: true,
    styled: true,
    utils: true,
  },
};
