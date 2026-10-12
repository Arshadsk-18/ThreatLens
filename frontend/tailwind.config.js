/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx,js,jsx}",
  ],
  darkMode: ["selector", "[data-theme='dark']"],
  theme: {
    container: {
      center: true,
      padding: "1.5rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      fontFamily: {
        display: ['"Bricolage Grotesque"', '"Instrument Sans"', 'system-ui', 'sans-serif'],
        sans: ['"Instrument Sans"', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      colors: {
        ink: {
          DEFAULT: "hsl(var(--ink))",
          muted: "hsl(var(--ink-muted))",
        },
        canvas: "hsl(var(--canvas))",
        surface: {
          DEFAULT: "hsl(var(--surface))",
          2: "hsl(var(--surface-2))",
        },
        hairline: "hsl(var(--hairline))",
        lens: {
          DEFAULT: "hsl(var(--lens))",
          muted: "hsl(var(--lens-muted))",
        },
        // Warm ramp (ONLY for severity)
        severity: {
          low: "hsl(var(--severity-low))",
          medium: "hsl(var(--severity-medium))",
          high: "hsl(var(--severity-high))",
          critical: "hsl(var(--severity-critical))",
        },
        // Cool ramp (ONLY for source status, never reuses severity hues)
        source: {
          live: "hsl(var(--source-live))",
          cached: "hsl(var(--source-cached))",
          simulated: "hsl(var(--source-simulated))",
          notconnected: "hsl(var(--source-notconnected))",
        },
      },
      borderRadius: {
        'panel': '24px',
        'nested': '16px',
        'pill': '9999px',
      },
      boxShadow: {
        'floating': 'var(--shadow-floating)',
      },
    },
  },
  plugins: [],
}
