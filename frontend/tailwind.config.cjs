/** @type {import('tailwindcss').Config} */
// Palette: Gunmetal Blue 60% (surfaces) / Warm Concrete 30% (sidebar, secondary) / Saffron Gold 10% (live accent)
module.exports = {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        gunmetal: { 950: "#1B2029", 900: "#222833", 800: "#2B3240", 700: "#3A4352" },
        concrete: "#B9B3A8",
        saffron: "#FFB800",
      },
      fontFamily: {
        sans: ["Mukta", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        devanagari: ["Mukta", '"Noto Sans Devanagari"', "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [require("daisyui")],
  daisyui: {
    themes: [
      {
        sandeshvani: {
          primary: "#FFB800",
          "primary-content": "#1B2029",
          secondary: "#B9B3A8",
          "secondary-content": "#222833",
          accent: "#FFD166",
          "accent-content": "#1B2029",
          neutral: "#1B2029",
          "neutral-content": "#E8E4DC",
          "base-100": "#2B3240",
          "base-200": "#222833",
          "base-300": "#3A4352",
          "base-content": "#E8E4DC",
          info: "#7FA6D6",
          "info-content": "#1B2029",
          success: "#5FCB8C",
          "success-content": "#1B2029",
          warning: "#FB923C",
          "warning-content": "#1B2029",
          error: "#F87171",
          "error-content": "#1B2029",
          "--rounded-box": "0.75rem",
          "--rounded-btn": "0.5rem",
        },
      },
    ],
    darkTheme: "sandeshvani",
    base: true,
    styled: true,
    utils: true,
  },
};

