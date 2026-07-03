/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: "#0A0E1A",
          secondary: "#0F1424",
          tertiary: "#151B2E",
          card: "#0E1322",
        },
        border: {
          default: "#1E2841",
          accent: "#2A3756",
        },
        text: {
          primary: "#E8ECF4",
          secondary: "#9AA5BD",
          tertiary: "#6B7793",
          muted: "#4A5570",
        },
        accent: {
          primary: "#5B8DEF",
          glow: "#7AABFF",
          success: "#3FCF8E",
          warning: "#F5A623",
          danger: "#EF5B5B",
          purple: "#9F7AEA",
          teal: "#38D9CD",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Menlo", "monospace"],
      },
      animation: {
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
        "shimmer": "shimmer 2s linear infinite",
        "fade-in": "fade-in 0.4s ease-out",
        "slide-up": "slide-up 0.3s ease-out",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": { opacity: "1", boxShadow: "0 0 20px rgba(91, 141, 239, 0.4)" },
          "50%": { opacity: "0.7", boxShadow: "0 0 30px rgba(91, 141, 239, 0.7)" },
        },
        "shimmer": {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
