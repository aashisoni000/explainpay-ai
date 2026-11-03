"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

const vertexShader = `
  attribute vec3 position;
  void main() {
    gl_Position = vec4(position, 1.0);
  }
`;

const fragmentShader = `
  precision highp float;
  uniform vec2 resolution;
  uniform float time;
  uniform float xScale;
  uniform float yScale;
  uniform float distortion;

  void main() {
    vec2 p = (gl_FragCoord.xy * 2.0 - resolution) / min(resolution.x, resolution.y);

    float d = length(p) * distortion;

    float rx = p.x * (1.0 + d);
    float gx = p.x;
    float bx = p.x * (1.0 - d);

    float r = 0.05 / abs(p.y + sin((rx + time) * xScale) * yScale);
    float g = 0.05 / abs(p.y + sin((gx + time) * xScale) * yScale);
    float b = 0.05 / abs(p.y + sin((bx + time) * xScale) * yScale);

    gl_FragColor = vec4(r, g, b, 1.0);
  }
`;

export function WebGLShader() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    let renderer: THREE.WebGLRenderer;

    try {
      renderer = new THREE.WebGLRenderer({ canvas, antialias: false });
    } catch (error) {
      console.warn("ExplainPay: WebGL unavailable; using dark background.", error);
      canvas.dataset.rendererStatus = "unavailable";
      return;
    }

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    const uniforms = {
      resolution: { value: new THREE.Vector2() },
      time: { value: 0 },
      xScale: { value: 1 },
      yScale: { value: 0.5 },
      distortion: { value: 0.05 },
    };
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(
        [
          -1, -1, 0, 1, -1, 0, -1, 1, 0,
          1, -1, 0, -1, 1, 0, 1, 1, 0,
        ],
        3,
      ),
    );
    const material = new THREE.RawShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms,
      side: THREE.DoubleSide,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.frustumCulled = false;
    scene.add(mesh);
    renderer.setClearColor(0x000000);

    const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
    let animationId: number | null = null;
    let previousTime: number | null = null;
    let contextLost = false;
    let shaderFailed = false;
    let disposed = false;

    const stop = () => {
      if (animationId !== null) cancelAnimationFrame(animationId);
      animationId = null;
      previousTime = null;
    };

    renderer.debug.onShaderError = (gl, program, vertex, fragment) => {
      shaderFailed = true;
      stop();
      canvas.style.visibility = "hidden";
      canvas.dataset.rendererStatus = "unavailable";
      console.error("ExplainPay: shader compilation failed.", {
        program: gl.getProgramInfoLog(program),
        vertex: gl.getShaderInfoLog(vertex),
        fragment: gl.getShaderInfoLog(fragment),
      });
    };

    const render = () => {
      if (!disposed && !contextLost && !shaderFailed) {
        renderer.render(scene, camera);
      }
    };

    const animate = (timestamp: number) => {
      animationId = null;
      if (disposed || contextLost || shaderFailed || document.hidden) return;
      if (previousTime !== null) {
        uniforms.time.value += Math.min((timestamp - previousTime) / 1000, 0.05) * 0.6;
      }
      previousTime = timestamp;
      render();
      if (!motionPreference.matches && !shaderFailed) {
        animationId = requestAnimationFrame(animate);
      }
    };

    const updateAnimation = () => {
      stop();
      if (contextLost || shaderFailed || document.hidden) return;
      render();
      canvas.dataset.rendererStatus = shaderFailed
        ? "unavailable"
        : motionPreference.matches ? "static" : "animated";
      if (!motionPreference.matches && !shaderFailed) {
        animationId = requestAnimationFrame(animate);
      }
    };

    const handleResize = () => {
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.setSize(window.innerWidth, window.innerHeight, false);
      // gl_FragCoord uses physical pixels, not CSS viewport dimensions.
      renderer.getDrawingBufferSize(uniforms.resolution.value);
      render();
    };

    const handleContextLost = (event: Event) => {
      event.preventDefault();
      contextLost = true;
      stop();
      canvas.style.visibility = "hidden";
      canvas.dataset.rendererStatus = "unavailable";
      console.warn("ExplainPay: WebGL context lost; using dark background.");
    };

    const handleContextRestored = () => {
      contextLost = false;
      canvas.style.visibility = "";
      handleResize();
      updateAnimation();
    };

    handleResize();
    updateAnimation();
    window.addEventListener("resize", handleResize);
    motionPreference.addEventListener("change", updateAnimation);
    document.addEventListener("visibilitychange", updateAnimation);
    canvas.addEventListener("webglcontextlost", handleContextLost);
    canvas.addEventListener("webglcontextrestored", handleContextRestored);

    return () => {
      disposed = true;
      stop();
      window.removeEventListener("resize", handleResize);
      motionPreference.removeEventListener("change", updateAnimation);
      document.removeEventListener("visibilitychange", updateAnimation);
      canvas.removeEventListener("webglcontextlost", handleContextLost);
      canvas.removeEventListener("webglcontextrestored", handleContextRestored);
      scene.remove(mesh);
      geometry.dispose();
      material.dispose();
      renderer.dispose();
    };
  }, []);

  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 bg-black">
      <canvas ref={canvasRef} className="block h-full w-full" />
    </div>
  );
}
