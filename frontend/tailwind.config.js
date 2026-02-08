/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{vue,js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'SF Pro Display', 'Roboto', 'Noto Sans', 'sans-serif'],
                mono: ['"Roboto Mono"', '"SF Mono"', 'Menlo', 'monospace'],
            },
        },
    },
    plugins: [],
}
