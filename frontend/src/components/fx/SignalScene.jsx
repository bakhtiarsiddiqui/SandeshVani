import { useEffect, useRef } from 'react';
import * as THREE from 'three';

/**
 * A dispatch going out: saffron rings radiate from a core across a disc of
 * recipients (golden-angle spiral). Dots light up as a ring passes them.
 * The disc tilts toward the cursor; submitting a form ("sv:dispatch") sends a burst.
 */
const R = 7.5; // disc radius
const COUNT = 560; // recipient dots
const MAX_RINGS = 6;
const SPEED = 2.4; // ring speed, units/sec
const EVERY = 3.2; // seconds between ambient pulses
const BASE_TILT = -1.05;

export default function SignalScene({ className = '' }) {
  const hostRef = useRef(null);

  useEffect(() => {
    const host = hostRef.current;
    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' });
    } catch {
      return; // no WebGL: the gunmetal backdrop stays, nothing breaks
    }
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.domElement.style.cssText = 'width:100%;height:100%;display:block';
    host.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
    const world = new THREE.Group();
    world.rotation.x = BASE_TILT;
    scene.add(world);

    const base = new THREE.Color('#B9B3A8');
    const hot = new THREE.Color('#FFB800');

    // recipients
    const pos = new Float32Array(COUNT * 3);
    const col = new Float32Array(COUNT * 3);
    const dist = new Float32Array(COUNT);
    for (let i = 0; i < COUNT; i++) {
      const r = R * Math.sqrt((i + 0.5) / COUNT);
      const a = i * 2.399963; // golden angle
      pos[i * 3] = Math.cos(a) * r;
      pos[i * 3 + 1] = Math.sin(a) * r;
      dist[i] = r;
    }
    const dotsGeo = new THREE.BufferGeometry();
    dotsGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    dotsGeo.setAttribute('color', new THREE.BufferAttribute(col, 3));
    // round dots (PointsMaterial draws squares by default)
    const dotCanvas = document.createElement('canvas');
    dotCanvas.width = dotCanvas.height = 64;
    const dctx = dotCanvas.getContext('2d');
    if (dctx) {
      dctx.beginPath();
      dctx.arc(32, 32, 30, 0, Math.PI * 2);
      dctx.fillStyle = '#fff';
      dctx.fill();
    }
    const dotTex = new THREE.CanvasTexture(dotCanvas);
    const dotsMat = new THREE.PointsMaterial({ size: 0.14, map: dotTex, alphaTest: 0.3, vertexColors: true, transparent: true, depthWrite: false });
    world.add(new THREE.Points(dotsGeo, dotsMat));

    // signal rings
    const ringGeo = new THREE.RingGeometry(0.992, 1, 192);
    const rings = Array.from({ length: MAX_RINGS }, () => {
      const mesh = new THREE.Mesh(
        ringGeo,
        new THREE.MeshBasicMaterial({ color: hot, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide }),
      );
      mesh.visible = false;
      world.add(mesh);
      return { mesh, r: 0, live: false };
    });
    const emit = () => {
      const free = rings.find((x) => !x.live);
      if (!free) return;
      free.live = true;
      free.r = 0.25;
      free.mesh.visible = true;
    };

    // core
    const coreGeo = new THREE.CircleGeometry(0.22, 40);
    const coreMat = new THREE.MeshBasicMaterial({ color: hot });
    const core = new THREE.Mesh(coreGeo, coreMat);
    world.add(core);

    const tint = new THREE.Color();
    const update = (dt) => {
      for (const ring of rings) {
        if (!ring.live) continue;
        ring.r += SPEED * dt;
        const t = ring.r / R;
        if (t >= 1.05) {
          ring.live = false;
          ring.mesh.visible = false;
          continue;
        }
        ring.mesh.scale.setScalar(ring.r);
        ring.mesh.material.opacity = 0.55 * (1 - t);
      }
      for (let i = 0; i < COUNT; i++) {
        let k = 0;
        for (const ring of rings) {
          if (!ring.live) continue;
          const d = Math.abs(dist[i] - ring.r);
          if (d < 0.7) k = Math.max(k, (1 - d / 0.7) * (1 - ring.r / R));
        }
        tint.copy(base).multiplyScalar(0.55).lerp(hot, k);
        col[i * 3] = tint.r;
        col[i * 3 + 1] = tint.g;
        col[i * 3 + 2] = tint.b;
      }
      dotsGeo.attributes.color.needsUpdate = true;
    };

    const render = () => renderer.render(scene, camera);

    const resize = () => {
      const w = host.clientWidth || 1;
      const h = host.clientHeight || 1;
      const aspect = w / h;
      renderer.setSize(w, h, false);
      camera.aspect = aspect;
      camera.position.z = aspect < 1.2 ? 17 + (1.2 - aspect) * 14 : 17;
      camera.updateProjectionMatrix();
      render();
    };
    const ro = new ResizeObserver(resize);
    ro.observe(host);
    resize();

    const timers = [];
    let stop = () => {};

    if (reduce) {
      // static frame: three frozen rings, no loop, no pointer tracking
      [2.2, 4.4, 6.4].forEach((r, i) => {
        emit();
        rings[i].r = r;
      });
      update(0);
      render();
    } else {
      const pointer = { x: 0, y: 0 };
      const tilt = { x: 0, y: 0 };
      const onMove = (e) => {
        pointer.x = (e.clientX / window.innerWidth) * 2 - 1;
        pointer.y = (e.clientY / window.innerHeight) * 2 - 1;
      };
      const onDispatch = () => {
        [0, 250, 500].forEach((ms) => timers.push(setTimeout(emit, ms)));
      };
      window.addEventListener('pointermove', onMove, { passive: true });
      window.addEventListener('sv:dispatch', onDispatch);

      let last = performance.now();
      let since = EVERY - 0.6; // first pulse shortly after load
      const tick = (now) => {
        const dt = Math.min((now - last) / 1000, 0.05);
        last = now;
        since += dt;
        if (since >= EVERY) {
          since = 0;
          emit();
        }
        const ease = Math.min(1, dt * 3);
        tilt.x += (pointer.y * 0.14 - tilt.x) * ease;
        tilt.y += (pointer.x * 1.4 - tilt.y) * ease;
        world.rotation.x = BASE_TILT + tilt.x;
        camera.position.x = tilt.y;
        camera.lookAt(0, 0, 0);
        core.scale.setScalar(1 + 0.15 * Math.sin(now / 330));
        update(dt);
        render();
      };
      const onVisibility = () => {
        last = performance.now();
        renderer.setAnimationLoop(document.hidden ? null : tick);
      };
      document.addEventListener('visibilitychange', onVisibility);
      renderer.setAnimationLoop(tick);

      stop = () => {
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('sv:dispatch', onDispatch);
        document.removeEventListener('visibilitychange', onVisibility);
      };
    }

    return () => {
      stop();
      timers.forEach(clearTimeout);
      ro.disconnect();
      renderer.setAnimationLoop(null);
      dotsGeo.dispose();
      dotsMat.dispose();
      dotTex.dispose();
      ringGeo.dispose();
      rings.forEach((r) => r.mesh.material.dispose());
      coreGeo.dispose();
      coreMat.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);

  return <div ref={hostRef} className={`h-full w-full ${className}`.trim()} />;
}
