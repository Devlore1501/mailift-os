import type { Config } from "tailwindcss";

// Design system PRD §12: navy scuro + oro, data-first.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#0C1420", // sfondo più profondo
          900: "#121D2B", // sfondo app
          800: "#15233F", // card / pannelli
          700: "#1D2F52", // bordi / hover
          600: "#2A4066",
        },
        gold: {
          400: "#F5A623",
          500: "#E0A93B",
          600: "#C08F2B",
        },
        ink: {
          100: "#EAF0F8", // testo primario
          300: "#B9C6D8", // testo secondario
          500: "#7D8DA3", // muted / vanity
        },
        ok: "#3DCB8F",
        warn: "#E5734B",
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 3px rgba(0,0,0,0.35)",
      },
    },
  },
  plugins: [],
} satisfies Config;
