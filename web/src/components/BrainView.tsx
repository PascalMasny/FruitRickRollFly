import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import type { Circuit, Frame } from '../lib/types'

interface Props {
  circuit: Circuit
  frame: Frame | null
  live: boolean
}

/* The palette is loud because the rest of the page is loud, but the three
   signals that carry meaning -- input, dopamine, aversion -- stay far apart in
   hue so you can still read them at a glance. */
const INK = {
  envelope: 0x3d2a6b,
  quiet: 0xb3a2ea,
  ear: 0x00e5ff,
  chroma: 0x7c4dff,
  kenyon: 0xfff3a0,
  dopamine: 0xffd400,
  aversion: 0xff2d95,
  tract: 0x5e4b8b,
}

/**
 * The circuit in three dimensions, sitting inside a ghost of the whole brain.
 *
 * The translucent envelope is the fly's brain as a shape -- two optic lobes
 * either side of a central mass. It is there for orientation and nothing else.
 * Everything bright inside it is a part of the model that actually computes:
 * Johnston's organ as a tonotopic ladder, the antennal lobe as a ball of
 * glomeruli, the calyx as a cloud of 4,000 Kenyon cells of which about 200 are
 * lit at any moment, the peduncle carrying their axons forward, and the
 * vertical and medial lobes where the two output compartments read them out.
 *
 * Neither the envelope nor the lobe geometry is measured anatomy. It is drawn
 * from the arrangement the textbooks describe, at the same level of fidelity
 * as the old flat schematic -- the shapes are ours, the wiring is the fly's.
 */
export default function BrainView({ circuit, frame, live }: Props) {
  const host = useRef<HTMLDivElement>(null)
  /* Everything the animation loop needs to touch, parked where the frame
     effect can reach it without rebuilding the scene. */
  const rig = useRef<{
    renderer: THREE.WebGLRenderer
    scene: THREE.Scene
    camera: THREE.PerspectiveCamera
    controls: OrbitControls
    kenyonColors: THREE.BufferAttribute
    kenyonSizes: THREE.BufferAttribute
    lit: Set<number>
    earBars: THREE.Mesh[]
    glomeruli: THREE.Mesh[]
    dan: { approach: THREE.Mesh; avoidance: THREE.Mesh }
    lobes: { approach: THREE.Mesh; avoidance: THREE.Mesh }
    calyxGlow: THREE.PointLight
    target: { dopamine: number; aversion: number }
  } | null>(null)

  // ── build the scene once ──────────────────────────────────────────────────
  useEffect(() => {
    const element = host.current
    if (!element) return

    const scene = new THREE.Scene()
    scene.fog = new THREE.FogExp2(0x0a0118, 0.035)

    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 200)
    camera.position.set(3.1, 2.9, 10.7)

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    element.appendChild(renderer.domElement)
    renderer.domElement.classList.add('brain-canvas')

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.06
    controls.enablePan = false
    controls.target.set(0.1, 0.6, 0.2)
    controls.minDistance = 6
    controls.maxDistance = 26
    controls.autoRotate = true
    controls.autoRotateSpeed = 0.75

    scene.add(new THREE.AmbientLight(0xffffff, 0.55))
    const key = new THREE.DirectionalLight(0xffffff, 0.9)
    key.position.set(6, 10, 8)
    scene.add(key)
    const rim = new THREE.DirectionalLight(INK.aversion, 0.35)
    rim.position.set(-8, -3, -6)
    scene.add(rim)

    // ── the ghost of the brain ──────────────────────────────────────────────
    const envelope = new THREE.Group()
    const shell = new THREE.MeshPhongMaterial({
      color: INK.envelope,
      transparent: true,
      opacity: 0.16,
      shininess: 60,
      side: THREE.DoubleSide,
      depthWrite: false,
    })
    const central = new THREE.Mesh(new THREE.SphereGeometry(3.2, 32, 24), shell)
    central.scale.set(1.25, 0.95, 0.85)
    envelope.add(central)
    for (const side of [-1, 1]) {
      // The optic lobes: the fly spends most of its brain on seeing, which is
      // worth showing given this model throws all of it away.
      const optic = new THREE.Mesh(new THREE.SphereGeometry(2.2, 28, 20), shell)
      optic.position.set(side * 4.6, 0.2, -0.3)
      optic.scale.set(0.78, 1.05, 0.95)
      envelope.add(optic)
    }
    const wire = new THREE.Mesh(
      new THREE.SphereGeometry(3.22, 18, 12),
      new THREE.MeshBasicMaterial({
        color: INK.envelope,
        wireframe: true,
        transparent: true,
        opacity: 0.17,
      }),
    )
    wire.scale.set(1.25, 0.95, 0.85)
    envelope.add(wire)
    scene.add(envelope)

    // ── Johnston's organ, which is a ring and not a ladder ──────────────────
    /* The real organ is a chordotonal array arranged radially around the
       antennal joint, so the receptors are drawn as a ring of radial spokes
       rather than the vertical bank the flat view used. Tonotopy runs round
       the circle; the twelve pitch classes are the inner ring. */
    const earBars: THREE.Mesh[] = []
    const earGroup = new THREE.Group()
    earGroup.position.set(-4.0, 0.3, 0.9)
    earGroup.rotation.y = -0.45
    const spoke = (length: number) => {
      const geometry = new THREE.BoxGeometry(length, 0.075, 0.075)
      // Origin at the inner end, so growing a spoke pushes it outward only.
      geometry.translate(length / 2, 0, 0)
      return geometry
    }
    const melSpoke = spoke(0.95)
    const chromaSpoke = spoke(0.6)
    const totalBands = circuit.melBands + circuit.chromaBands
    for (let i = 0; i < totalBands; i += 1) {
      const isChroma = i >= circuit.melBands
      const index = isChroma ? i - circuit.melBands : i
      const span = isChroma ? circuit.chromaBands : circuit.melBands
      const bar = new THREE.Mesh(
        isChroma ? chromaSpoke : melSpoke,
        new THREE.MeshPhongMaterial({
          color: isChroma ? INK.chroma : INK.ear,
          emissive: isChroma ? INK.chroma : INK.ear,
          emissiveIntensity: 0,
          shininess: 90,
        }),
      )
      const theta = (index / span) * Math.PI * 2
      const ring = isChroma ? 0.38 : 0.9
      bar.position.set(Math.cos(theta) * ring, Math.sin(theta) * ring, 0)
      bar.rotation.z = theta
      bar.scale.x = 0.25
      earGroup.add(bar)
      earBars.push(bar)
    }
    const earHub = new THREE.Mesh(
      new THREE.TorusGeometry(0.88, 0.04, 8, 48),
      new THREE.MeshPhongMaterial({ color: INK.tract, emissive: INK.tract, emissiveIntensity: 0.3 }),
    )
    earGroup.add(earHub)
    scene.add(earGroup)

    // ── antennal lobe: a ball of glomeruli ──────────────────────────────────
    const glomeruli: THREE.Mesh[] = []
    const alCentre = new THREE.Vector3(-2.6, -1.4, 1.1)
    const alCore = new THREE.Mesh(
      new THREE.SphereGeometry(0.88, 20, 16),
      new THREE.MeshPhongMaterial({ color: INK.quiet, transparent: true, opacity: 0.5 }),
    )
    alCore.position.copy(alCentre)
    scene.add(alCore)
    const GLOMERULI = 18
    for (let i = 0; i < GLOMERULI; i += 1) {
      // Fibonacci sphere, so the glomeruli sit evenly on the surface.
      const y = 1 - (i / (GLOMERULI - 1)) * 2
      const radius = Math.sqrt(Math.max(0, 1 - y * y))
      const theta = Math.PI * (3 - Math.sqrt(5)) * i
      const blob = new THREE.Mesh(
        new THREE.SphereGeometry(0.33, 14, 12),
        new THREE.MeshPhongMaterial({
          color: INK.ear,
          emissive: INK.ear,
          emissiveIntensity: 0,
          shininess: 80,
        }),
      )
      blob.position.set(
        alCentre.x + Math.cos(theta) * radius * 0.88,
        alCentre.y + y * 0.88,
        alCentre.z + Math.sin(theta) * radius * 0.88,
      )
      scene.add(blob)
      glomeruli.push(blob)
    }

    // ── the calyx, and 4,000 Kenyon cells inside it ─────────────────────────
    const calyxCentre = new THREE.Vector3(-0.2, 1.7, -0.7)
    const calyx = new THREE.Mesh(
      new THREE.SphereGeometry(1.95, 24, 18),
      new THREE.MeshPhongMaterial({
        color: INK.envelope,
        transparent: true,
        opacity: 0.3,
        side: THREE.DoubleSide,
        depthWrite: false,
      }),
    )
    calyx.position.copy(calyxCentre)
    calyx.scale.set(1.1, 0.82, 1.0)
    scene.add(calyx)

    const count = circuit.kenyonCells
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)
    const sizes = new Float32Array(count)
    // The same seeded scatter the flat view used, so the calyx is the same
    // cloud every reload and a cell keeps its place between songs.
    let seed = 1987
    const random = () => {
      seed = (seed * 1664525 + 1013904223) >>> 0
      return seed / 4294967296
    }
    const quiet = new THREE.Color(INK.quiet)
    for (let i = 0; i < count; i += 1) {
      let x = 0
      let y = 0
      let z = 0
      do {
        x = random() * 2 - 1
        y = random() * 2 - 1
        z = random() * 2 - 1
      } while (x * x + y * y + z * z > 1)
      positions[i * 3] = calyxCentre.x + x * 2.0
      positions[i * 3 + 1] = calyxCentre.y + y * 1.5
      positions[i * 3 + 2] = calyxCentre.z + z * 1.85
      colors[i * 3] = quiet.r
      colors[i * 3 + 1] = quiet.g
      colors[i * 3 + 2] = quiet.b
      sizes[i] = 0.12
    }
    const kenyonGeometry = new THREE.BufferGeometry()
    kenyonGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    const kenyonColors = new THREE.BufferAttribute(colors, 3)
    const kenyonSizes = new THREE.BufferAttribute(sizes, 1)
    kenyonGeometry.setAttribute('color', kenyonColors)
    kenyonGeometry.setAttribute('size', kenyonSizes)
    /* A tiny shader rather than PointsMaterial: the firing cells need to be
       both brighter and bigger than the silent ones, and PointsMaterial has
       one size for the whole cloud. */
    const kenyonMaterial = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      vertexShader: `
        attribute float size;
        varying vec3 vColor;
        void main() {
          vColor = color;
          vec4 mv = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = size * (320.0 / -mv.z);
          gl_Position = projectionMatrix * mv;
        }
      `,
      fragmentShader: `
        varying vec3 vColor;
        void main() {
          float d = length(gl_PointCoord - vec2(0.5));
          if (d > 0.5) discard;
          gl_FragColor = vec4(vColor, smoothstep(0.5, 0.05, d));
        }
      `,
      vertexColors: true,
    })
    scene.add(new THREE.Points(kenyonGeometry, kenyonMaterial))

    const calyxGlow = new THREE.PointLight(INK.dopamine, 0, 9)
    calyxGlow.position.copy(calyxCentre)
    scene.add(calyxGlow)

    // ── tracts: antenna → lobe → calyx → peduncle → lobes ───────────────────
    const tractMaterial = new THREE.MeshPhongMaterial({
      color: INK.tract,
      emissive: INK.tract,
      emissiveIntensity: 0.25,
      shininess: 70,
    })
    const tube = (points: THREE.Vector3[], radius: number, material = tractMaterial) =>
      new THREE.Mesh(
        new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points), 44, radius, 10, false),
        material,
      )

    scene.add(
      tube(
        [
          new THREE.Vector3(-3.9, 0.2, 0.9),
          new THREE.Vector3(-3.3, -0.8, 1.0),
          alCentre.clone(),
        ],
        0.11,
      ),
    )
    // The projection-neuron tract, which in the fly loops laterally on its way
    // up to the calyx rather than running straight.
    scene.add(
      tube(
        [
          alCentre.clone(),
          new THREE.Vector3(-2.4, 0.2, 0.3),
          new THREE.Vector3(-1.6, 1.3, -1.2),
          calyxCentre.clone(),
        ],
        0.13,
      ),
    )
    // The peduncle: every Kenyon axon leaving the calyx as one bundle.
    const heel = new THREE.Vector3(1.2, -0.7, 0.6)
    scene.add(
      tube([calyxCentre.clone(), new THREE.Vector3(0.5, 0.6, -0.1), heel.clone()], 0.28),
    )

    const lobeMaterial = (colour: number) =>
      new THREE.MeshPhongMaterial({
        color: colour,
        emissive: colour,
        emissiveIntensity: 0.12,
        shininess: 90,
        transparent: true,
        opacity: 0.92,
      })

    // Vertical lobe, read out as avoidance and taught by PPL1.
    const avoidanceLobe = tube(
      [heel.clone(), new THREE.Vector3(1.4, 0.9, 0.9), new THREE.Vector3(1.6, 2.7, 1.2)],
      0.3,
      lobeMaterial(INK.aversion),
    )
    scene.add(avoidanceLobe)
    // Medial lobe, read out as approach and taught by PAM.
    const approachLobe = tube(
      [heel.clone(), new THREE.Vector3(2.6, -1.1, 1.1), new THREE.Vector3(4.1, -1.4, 1.5)],
      0.3,
      lobeMaterial(INK.dopamine),
    )
    scene.add(approachLobe)

    const danMesh = (colour: number, at: THREE.Vector3) => {
      const mesh = new THREE.Mesh(
        new THREE.SphereGeometry(0.33, 18, 14),
        new THREE.MeshPhongMaterial({
          color: colour,
          emissive: colour,
          emissiveIntensity: 0.1,
          shininess: 100,
        }),
      )
      mesh.position.copy(at)
      scene.add(mesh)
      return mesh
    }
    const danAvoidance = danMesh(INK.aversion, new THREE.Vector3(1.7, 3.3, 1.3))
    const danApproach = danMesh(INK.dopamine, new THREE.Vector3(4.7, -1.5, 1.6))

    // ── resize, loop, teardown ──────────────────────────────────────────────
    /* The panel is a wide box on a desktop and a tall one on a phone, and the
       animal is wider than it is high. Holding the vertical field of view
       fixed would crop the antenna off the side of a narrow panel, so the
       vertical angle opens up instead to keep the horizontal coverage
       constant. Zoom is left alone: widening the lens does not fight the
       distance the viewer chose. */
    const BASE_FOV = 42
    const BASE_ASPECT = 1.5
    const resize = () => {
      const { clientWidth: w, clientHeight: h } = element
      if (w === 0 || h === 0) return
      renderer.setSize(w, h, false)
      const aspect = w / h
      camera.aspect = aspect
      if (aspect >= BASE_ASPECT) {
        camera.fov = BASE_FOV
      } else {
        const half = Math.tan((BASE_FOV * Math.PI) / 360) * (BASE_ASPECT / aspect)
        camera.fov = Math.min(84, (Math.atan(half) * 360) / Math.PI)
      }
      camera.updateProjectionMatrix()
    }
    const observer = new ResizeObserver(resize)
    observer.observe(element)
    resize()

    const state = {
      renderer,
      scene,
      camera,
      controls,
      kenyonColors,
      kenyonSizes,
      lit: new Set<number>(),
      earBars,
      glomeruli,
      dan: { approach: danApproach, avoidance: danAvoidance },
      lobes: { approach: approachLobe, avoidance: avoidanceLobe },
      calyxGlow,
      target: { dopamine: 0, aversion: 0 },
    }
    rig.current = state

    let raf = 0
    const clock = new THREE.Clock()
    const tick = () => {
      raf = requestAnimationFrame(tick)
      const t = clock.getElapsedTime()
      controls.update()
      // The pools breathe a little so a held value still looks alive.
      const pulse = 0.85 + 0.15 * Math.sin(t * 3.1)
      const { dopamine, aversion } = state.target
      ;(state.dan.approach.material as THREE.MeshPhongMaterial).emissiveIntensity =
        0.1 + 1.5 * dopamine * pulse
      ;(state.dan.avoidance.material as THREE.MeshPhongMaterial).emissiveIntensity =
        0.1 + 1.5 * aversion * pulse
      ;(state.lobes.approach.material as THREE.MeshPhongMaterial).emissiveIntensity =
        0.12 + 0.75 * dopamine
      ;(state.lobes.avoidance.material as THREE.MeshPhongMaterial).emissiveIntensity =
        0.12 + 0.75 * aversion
      state.calyxGlow.intensity = 5.5 * dopamine * pulse
      renderer.render(scene, camera)
    }
    tick()

    return () => {
      cancelAnimationFrame(raf)
      observer.disconnect()
      controls.dispose()
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Points) {
          object.geometry.dispose()
          const material = object.material
          if (Array.isArray(material)) material.forEach((m) => m.dispose())
          else material.dispose()
        }
      })
      renderer.dispose()
      renderer.domElement.remove()
      rig.current = null
    }
  }, [circuit.kenyonCells, circuit.melBands, circuit.chromaBands])

  // ── push each percept into the scene ──────────────────────────────────────
  useEffect(() => {
    const state = rig.current
    if (!state) return

    state.target.dopamine = Math.min(1, frame?.dopamine ?? 0)
    state.target.aversion = Math.min(1, frame?.aversion ?? 0)

    const colors = state.kenyonColors
    const sizes = state.kenyonSizes
    const quiet = new THREE.Color(INK.quiet)
    const hot = new THREE.Color(INK.kenyon)
    // Only the cells that changed state are touched: repainting all 4,000
    // every 128 ms is most of a frame's budget for no visible gain.
    for (const i of state.lit) {
      colors.setXYZ(i, quiet.r, quiet.g, quiet.b)
      sizes.setX(i, 0.12)
    }
    state.lit.clear()
    for (const i of frame?.kenyon ?? []) {
      if (i < 0 || i >= sizes.count) continue
      colors.setXYZ(i, hot.r, hot.g, hot.b)
      sizes.setX(i, 0.34)
      state.lit.add(i)
    }
    colors.needsUpdate = true
    sizes.needsUpdate = true

    const ear = frame?.ear ?? []
    for (let i = 0; i < state.earBars.length; i += 1) {
      const value = Math.max(0, Math.min(1, ear[i] ?? 0))
      const bar = state.earBars[i]
      bar.scale.x = 0.25 + value * 1.3
      ;(bar.material as THREE.MeshPhongMaterial).emissiveIntensity = value * 1.5
    }
    // Each glomerulus pools the channels beneath it, as the real one pools
    // receptors of a single type.
    for (let i = 0; i < state.glomeruli.length; i += 1) {
      const lo = Math.floor((i / state.glomeruli.length) * ear.length)
      const hi = Math.max(lo + 1, Math.floor(((i + 1) / state.glomeruli.length) * ear.length))
      let sum = 0
      for (let j = lo; j < hi; j += 1) sum += ear[j] ?? 0
      const value = ear.length ? Math.min(1, sum / (hi - lo)) : 0
      const blob = state.glomeruli[i]
      ;(blob.material as THREE.MeshPhongMaterial).emissiveIntensity = value * 1.6
      blob.scale.setScalar(1 + value * 0.45)
    }
  }, [frame])

  return (
    <div className="brain-stage">
      <div ref={host} className="brain-host" />
      <div className="brain-hud">
        <span className="brain-hud-left">
          {live ? `${frame?.kenyon.length ?? 0} / ${circuit.kenyonCells} KENYON CELLS FIRING` : 'FLY AT REST'}
        </span>
        <span className="brain-hud-right">drag to spin &middot; scroll to zoom</span>
      </div>
    </div>
  )
}
