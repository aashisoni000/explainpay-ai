# ExplainPay

A cinematic financial trust intelligence homepage built with Next.js 16 App
Router, TypeScript, Tailwind CSS, Three.js, Lucide React, and Geist.

## Development

```bash
npm install
npm run dev
```

Open http://localhost:3000.

```bash
npm run lint
npx tsc --noEmit
npm run build
```

## Homepage

The full-screen background in `components/ui/web-gl-shader.tsx` uses the supplied
vertex and fragment shaders with Three.js `RawShaderMaterial`. Drawing-buffer
resolution tracks device pixel ratio (capped at 2). Animation is time-based,
pauses in hidden tabs, and renders a still frame for reduced-motion preferences.
A solid black background remains if WebGL is unavailable or its context is lost.
GPU resources, animation frames, and listeners are released on unmount.

The keyboard-accessible selection cards use Next.js links to `/transactions`
and `/website-scanner`. These destination tools are not implemented in this
homepage-only project.

Geist is loaded using `next/font/google`; the initial build requires access to
Google Fonts.
