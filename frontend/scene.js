/* ============================================================
   AEGIS · Ezor Media
   Hero 3D: a liquid chrome form, plus page motion.
   Loaded as a module. Fails quietly if WebGL or the CDN is
   unavailable, so the page always renders.
   ============================================================ */
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

bootMotion();
boot3D();

/* ----------------------------------------------------------------
   Motion (Motion One, same engine family as Framer Motion)
   ---------------------------------------------------------------- */
async function bootMotion() {
  const hero = document.querySelectorAll("[data-animate]");
  const reveals = document.querySelectorAll("[data-reveal]");

  if (reduce) {
    [...hero, ...reveals].forEach((el) => (el.style.opacity = 1));
    return;
  }

  let animate, inView, stagger;
  try {
    ({ animate, inView, stagger } = await import(
      "https://cdn.jsdelivr.net/npm/motion@10.18.0/+esm"
    ));
  } catch (e) {
    [...hero, ...reveals].forEach((el) => (el.style.opacity = 1));
    return;
  }

  if (hero.length) {
    animate(
      hero,
      { opacity: [0, 1], y: [22, 0] },
      { delay: stagger(0.09, { start: 0.15 }), duration: 0.8, easing: [0.16, 1, 0.3, 1] }
    );
  }

  reveals.forEach((el) => {
    el.style.opacity = 0;
    const stop = inView(
      el,
      () => {
        animate(
          el,
          { opacity: [0, 1], y: [26, 0] },
          { duration: 0.7, easing: [0.16, 1, 0.3, 1] }
        );
        if (stop) stop();
      },
      { margin: "-90px" }
    );
  });
}

/* ----------------------------------------------------------------
   Liquid chrome 3D
   ---------------------------------------------------------------- */
function boot3D() {
  const canvas = document.getElementById("heroCanvas");
  if (!canvas) return;

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: "high-performance",
    });
  } catch (e) {
    canvas.style.display = "none";
    return;
  }

  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.3;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
  camera.position.set(0, 0, 4.6);

  // studio reflections for the chrome, no external files needed
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.02).texture;

  // high-detail sphere we deform on the GPU into liquid metal
  const geo = new THREE.IcosahedronGeometry(1.55, 56);
  const mat = new THREE.MeshPhysicalMaterial({
    color: 0xeef0f3,
    metalness: 1.0,
    roughness: 0.045,
    envMapIntensity: 2.1,
    clearcoat: 0.6,
    clearcoatRoughness: 0.1,
  });

  const NOISE = `
    vec3 aMod289(vec3 x){return x - floor(x*(1.0/289.0))*289.0;}
    vec4 aMod289(vec4 x){return x - floor(x*(1.0/289.0))*289.0;}
    vec4 aPermute(vec4 x){return aMod289(((x*34.0)+1.0)*x);}
    vec4 aTaylor(vec4 r){return 1.79284291400159 - 0.85373472095314 * r;}
    float aSnoise(vec3 v){
      const vec2 C = vec2(1.0/6.0, 1.0/3.0);
      const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
      vec3 i  = floor(v + dot(v, C.yyy));
      vec3 x0 = v - i + dot(i, C.xxx);
      vec3 g = step(x0.yzx, x0.xyz);
      vec3 l = 1.0 - g;
      vec3 i1 = min(g.xyz, l.zxy);
      vec3 i2 = max(g.xyz, l.zxy);
      vec3 x1 = x0 - i1 + C.xxx;
      vec3 x2 = x0 - i2 + C.yyy;
      vec3 x3 = x0 - D.yyy;
      i = aMod289(i);
      vec4 p = aPermute(aPermute(aPermute(
                 i.z + vec4(0.0, i1.z, i2.z, 1.0))
               + i.y + vec4(0.0, i1.y, i2.y, 1.0))
               + i.x + vec4(0.0, i1.x, i2.x, 1.0));
      float n_ = 0.142857142857;
      vec3 ns = n_ * D.wyz - D.xzx;
      vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
      vec4 x_ = floor(j * ns.z);
      vec4 y_ = floor(j - 7.0 * x_);
      vec4 x = x_ * ns.x + ns.yyyy;
      vec4 y = y_ * ns.x + ns.yyyy;
      vec4 h = 1.0 - abs(x) - abs(y);
      vec4 b0 = vec4(x.xy, y.xy);
      vec4 b1 = vec4(x.zw, y.zw);
      vec4 s0 = floor(b0)*2.0 + 1.0;
      vec4 s1 = floor(b1)*2.0 + 1.0;
      vec4 sh = -step(h, vec4(0.0));
      vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
      vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
      vec3 q0 = vec3(a0.xy, h.x);
      vec3 q1 = vec3(a0.zw, h.y);
      vec3 q2 = vec3(a1.xy, h.z);
      vec3 q3 = vec3(a1.zw, h.w);
      vec4 norm = aTaylor(vec4(dot(q0,q0), dot(q1,q1), dot(q2,q2), dot(q3,q3)));
      q0 *= norm.x; q1 *= norm.y; q2 *= norm.z; q3 *= norm.w;
      vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
      m = m * m;
      return 42.0 * dot(m*m, vec4(dot(q0,x0), dot(q1,x1), dot(q2,x2), dot(q3,x3)));
    }
    float aDisp(vec3 p){
      float d  = aSnoise(p * uFreq + vec3(0.0, 0.0, uTime)) * uAmp;
      d += aSnoise(p * uFreq * 2.1 + vec3(uTime * 1.25)) * uAmp * 0.22;
      return d;
    }
  `;

  mat.onBeforeCompile = (shader) => {
    shader.uniforms.uTime = { value: 0 };
    shader.uniforms.uAmp = { value: 0.3 };
    shader.uniforms.uFreq = { value: 0.6 };

    shader.vertexShader = shader.vertexShader
      .replace(
        "#include <common>",
        `#include <common>\nuniform float uTime;\nuniform float uAmp;\nuniform float uFreq;\n${NOISE}`
      )
      .replace(
        "#include <beginnormal_vertex>",
        `
        vec3 aN = normalize(position);
        vec3 aUp = abs(aN.y) < 0.99 ? vec3(0.0,1.0,0.0) : vec3(1.0,0.0,0.0);
        vec3 aTan = normalize(cross(aN, aUp));
        vec3 aBit = normalize(cross(aN, aTan));
        float aEps = 0.08;
        vec3 aP  = position + aN * aDisp(position);
        vec3 aPt = position + aTan * aEps; aPt += normalize(aPt) * aDisp(aPt);
        vec3 aPb = position + aBit * aEps; aPb += normalize(aPb) * aDisp(aPb);
        vec3 objectNormal = normalize(cross(aPt - aP, aPb - aP));
        `
      )
      .replace(
        "#include <begin_vertex>",
        `vec3 transformed = position + normalize(position) * aDisp(position);`
      );

    mat.userData.shader = shader;
  };

  const blob = new THREE.Mesh(geo, mat);

  const pivot = new THREE.Group();
  pivot.add(blob);
  scene.add(pivot);

  // light to lift the chrome on top of the environment reflections
  const key = new THREE.DirectionalLight(0xffffff, 2.4);
  key.position.set(3, 4, 5);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xcdd8e6, 1.3);
  fill.position.set(-3, -1, 2);
  scene.add(fill);
  scene.add(new THREE.AmbientLight(0x47474f, 0.5));

  // faint sterling dust for depth
  scene.add(makeParticles());

  // sizing
  function resize() {
    const r = canvas.getBoundingClientRect();
    const w = Math.max(1, r.width);
    const h = Math.max(1, r.height);
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  resize();
  new ResizeObserver(resize).observe(canvas);

  // pointer parallax
  let px = 0, py = 0, gx = 0, gy = 0;
  window.addEventListener(
    "pointermove",
    (e) => {
      px = e.clientX / window.innerWidth - 0.5;
      py = e.clientY / window.innerHeight - 0.5;
    },
    { passive: true }
  );

  const clock = new THREE.Clock();
  let raf = null;
  let running = false;

  function frame() {
    raf = requestAnimationFrame(frame);
    const t = clock.getElapsedTime();

    const sh = mat.userData.shader;
    if (sh) sh.uniforms.uTime.value = reduce ? 0.6 : t * 0.32;

    if (!reduce) {
      blob.rotation.y += 0.001;
      pivot.position.y = Math.sin(t * 0.45) * 0.04;
    }

    // ease the whole piece toward the pointer for parallax
    const ty = px * 0.5;
    const tx = -py * 0.4;
    gy += (ty - gy) * 0.05;
    gx += (tx - gx) * 0.05;
    pivot.rotation.y = gy;
    pivot.rotation.x = gx;

    scene.children.forEach((c) => {
      if (c.isPoints && !reduce) c.rotation.y = t * 0.02;
    });

    renderer.render(scene, camera);
  }

  function start() {
    if (running) return;
    running = true;
    clock.start();
    frame();
  }
  function stop() {
    running = false;
    if (raf) cancelAnimationFrame(raf);
    raf = null;
  }

  // the blob is a site-wide background, so it runs continuously and only
  // pauses when the tab is hidden, to save the GPU.
  document.addEventListener("visibilitychange", () => {
    document.hidden ? stop() : start();
  });

  start();
}

function makeParticles() {
  const n = 150;
  const pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    const r = 2.7 + Math.random() * 2.4;
    const th = Math.random() * Math.PI * 2;
    const ph = Math.acos(2 * Math.random() - 1);
    pos[i * 3] = r * Math.sin(ph) * Math.cos(th);
    pos[i * 3 + 1] = r * Math.sin(ph) * Math.sin(th);
    pos[i * 3 + 2] = r * Math.cos(ph);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const m = new THREE.PointsMaterial({
    color: 0xcfd4da,
    size: 0.02,
    transparent: true,
    opacity: 0.5,
    depthWrite: false,
    sizeAttenuation: true,
  });
  return new THREE.Points(g, m);
}
