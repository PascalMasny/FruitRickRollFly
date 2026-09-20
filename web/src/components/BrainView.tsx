import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import type { Circuit, Frame } from '../lib/types'

interface Props {
  circuit: Circuit
  frame: Frame | null
  live: boolean
}

const INK = {
  chitin: 0x14110d,
  circuit: 0x3a3126,
  context: 0x161310,
  quiet: 0x9c8f77,
  kenyon: 0xf2e4c0,
  approach: 0xe0912f,
  avoidance: 0xb3121f,
}

/* Which surface plays which part. The names are the ones the extractor wrote
   into the GLB, which are the hemibrain's own ROIs under plainer labels. */
const APPROACH = new Set(['beta', 'beta-prime', 'gamma'])
const AVOIDANCE = new Set(['alpha', 'alpha-prime'])
const CONTEXT = new Set(['lateral-horn', 'medulla', 'lobula', 'lobula-plate'])

/**
 * The mushroom body as it was actually measured.
 *
 * Every surface here is a neuropil from the Janelia FlyEM hemibrain v1.2 ROI
 * segmentation, pulled by `frrf-meshes` and shipped as a GLB: the calyx, the
 * peduncle, the five lobes, the antennal lobe, and -- drawn nearly black,
 * because this model throws all of it away -- the lateral horn and the three
 * optic neuropils. Nothing in this scene is a shape we invented.
 *
 * The 4,000 Kenyon cells are scattered inside the real calyx surface, sampled
 * once at build time and rejected against the mesh, so a lit cell is lit
 * somewhere a Kenyon cell could actually be. The lobes glow with the pool that
 * reads them: amber on the medial lobes for approach, red on the vertical
 * ones for avoidance.
 *
 * Johnston's organ is deliberately absent. It is not in the brain and not in
 * this dataset, and inventing an antenna to sit next to measured anatomy would
 * undo the point of measuring it. The receptors are drawn flat, in the panel.
 */
export default function BrainView({ circuit, frame, live }: Props) {
  const host = useRef<HTMLDivElement>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'failed'>('loading')
  const rig = useRef<{
    kenyonColors: THREE.BufferAttribute
    kenyonSizes: THREE.BufferAttribute
    lit: Set<number>
    approach: THREE.MeshStandardMaterial[]
    avoidance: THREE.MeshStandardMaterial[]
    antennalLobe: THREE.MeshStandardMaterial | null
    calyxGlow: THREE.PointLight
    target: { dopamine: number; aversion: number; drive: number }
  } | null>(null)

  useEffect(() => {
    const element = host.current
    if (!element) return
    let disposed = false

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 400)
    camera.position.set(6, 3.8, 11)

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.4
    element.appendChild(renderer.domElement)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.06
    controls.enablePan = false
    controls.minDistance = 6
    controls.maxDistance = 40
    controls.autoRotate = true
    controls.autoRotateSpeed = 0.55

    /* Warm key, cold fill, cold rim. An earlier orange rim made the optic
       lobes look like raw meat, which is not the note we are going for. */
    scene.add(new THREE.AmbientLight(0xffffff, 0.8))
    const key = new THREE.DirectionalLight(0xfff2e0, 2.1)
    key.position.set(5, 9, 7)
    scene.add(key)
    const rim = new THREE.DirectionalLight(0xa8bed4, 0.7)
    rim.position.set(-7, -2, -8)
    scene.add(rim)
    const fill = new THREE.DirectionalLight(0x8fa2bd, 0.7)
    fill.position.set(-6, 3, 5)
    scene.add(fill)

    const calyxGlow = new THREE.PointLight(INK.approach, 0, 14, 2)
    scene.add(calyxGlow)

    const state = {
      kenyonColors: null as unknown as THREE.BufferAttribute,
      kenyonSizes: null as unknown as THREE.BufferAttribute,
      lit: new Set<number>(),
      approach: [] as THREE.MeshStandardMaterial[],
      avoidance: [] as THREE.MeshStandardMaterial[],
      antennalLobe: null as THREE.MeshStandardMaterial | null,
      calyxGlow,
      target: { dopamine: 0, aversion: 0, drive: 0 },
    }

    const surface = (name: string) => {
      const approach = APPROACH.has(name)
      const avoidance = AVOIDANCE.has(name)
      const context = CONTEXT.has(name)
      const material = new THREE.MeshStandardMaterial({
        color: approach ? 0x3a2a14 : avoidance ? 0x331014 : context ? INK.context : INK.circuit,
        emissive: approach ? INK.approach : avoidance ? INK.avoidance : 0x000000,
        emissiveIntensity: 0,
        roughness: context ? 1.0 : 0.5,
        metalness: 0.15,
        transparent: true,
        // The ROI meshes are not watertight and their winding is inverted, so
        // both faces are drawn rather than trusting the normals.
        side: THREE.DoubleSide,
        opacity: context ? 0.12 : name === 'calyx' ? 0.16 : 0.92,
        depthWrite: !context && name !== 'calyx',
      })
      if (approach) state.approach.push(material)
      if (avoidance) state.avoidance.push(material)
      if (name === 'antennal-lobe') state.antennalLobe = material
      return material
    }

    const loadPoints = fetch('kenyon-cells.bin').then(async (response) => {
      if (!response.ok) throw new Error(`kenyon-cells.bin: ${response.status}`)
      return new Float32Array(await response.arrayBuffer())
    })
    const loadMeshes = new GLTFLoader().loadAsync('fly-brain.glb')

    Promise.all([loadMeshes, loadPoints])
      .then(([gltf, pool]) => {
        if (disposed) return

        gltf.scene.traverse((object) => {
          if (!(object instanceof THREE.Mesh)) return
          const name = object.name.toLowerCase().replace(/[^a-z-]/g, '')
          object.material = surface(name)
          object.geometry.computeVertexNormals()
        })
        scene.add(gltf.scene)

        // The build ships a pool; the page takes as many as the fly has.
        const count = Math.min(circuit.kenyonCells, Math.floor(pool.length / 3))
        const positions = pool.slice(0, count * 3)
        const colors = new Float32Array(count * 3)
        const sizes = new Float32Array(count)
        const quiet = new THREE.Color(INK.quiet)
        for (let i = 0; i < count; i += 1) {
          colors[i * 3] = quiet.r
          colors[i * 3 + 1] = quiet.g
          colors[i * 3 + 2] = quiet.b
          sizes[i] = 0.055
        }
        const geometry = new THREE.BufferGeometry()
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
        const colorAttr = new THREE.BufferAttribute(colors, 3)
        const sizeAttr = new THREE.BufferAttribute(sizes, 1)
        geometry.setAttribute('color', colorAttr)
        geometry.setAttribute('size', sizeAttr)
        state.kenyonColors = colorAttr
        state.kenyonSizes = sizeAttr

        /* A shader rather than PointsMaterial: a firing cell has to be both
           brighter and larger than a silent one, and PointsMaterial has a
           single size for the whole cloud. */
        const points = new THREE.Points(
          geometry,
          new THREE.ShaderMaterial({
            transparent: true,
            depthWrite: false,
            blending: THREE.AdditiveBlending,
            vertexColors: true,
            vertexShader: `
              attribute float size;
              varying vec3 vColor;
              void main() {
                vColor = color;
                vec4 mv = modelViewMatrix * vec4(position, 1.0);
                gl_PointSize = size * (340.0 / -mv.z);
                gl_Position = projectionMatrix * mv;
              }
            `,
            fragmentShader: `
              varying vec3 vColor;
              void main() {
                float d = length(gl_PointCoord - vec2(0.5));
                if (d > 0.5) discard;
                gl_FragColor = vec4(vColor, smoothstep(0.5, 0.0, d));
              }
            `,
          }),
        )
        scene.add(points)

        // Park the glow at the centre of the calyx cloud.
        geometry.computeBoundingSphere()
        if (geometry.boundingSphere) calyxGlow.position.copy(geometry.boundingSphere.center)

        rig.current = state
        setStatus('ready')
      })
      .catch((error) => {
        console.error('brain meshes', error)
        if (!disposed) setStatus('failed')
      })

    /* The panel is a wide box on a desktop and a tall one on a phone. Holding
       the vertical field of view fixed would crop the animal off the side of a
       narrow panel, so the vertical angle opens instead, keeping horizontal
       coverage constant without fighting the viewer's zoom. */
    const BASE_FOV = 40
    const BASE_ASPECT = 1.5
    const resize = () => {
      const { clientWidth: w, clientHeight: h } = element
      if (w === 0 || h === 0) return
      renderer.setSize(w, h, false)
      const aspect = w / h
      camera.aspect = aspect
      camera.fov =
        aspect >= BASE_ASPECT
          ? BASE_FOV
          : Math.min(
              84,
              (Math.atan(Math.tan((BASE_FOV * Math.PI) / 360) * (BASE_ASPECT / aspect)) * 360) /
                Math.PI,
            )
      camera.updateProjectionMatrix()
    }
    const observer = new ResizeObserver(resize)
    observer.observe(element)
    resize()

    let raf = 0
    const clock = new THREE.Clock()
    const tick = () => {
      raf = requestAnimationFrame(tick)
      const t = clock.getElapsedTime()
      controls.update()
      const pulse = 0.88 + 0.12 * Math.sin(t * 2.7)
      const { dopamine, aversion, drive } = state.target
      for (const material of state.approach) material.emissiveIntensity = 1.9 * dopamine * pulse
      for (const material of state.avoidance) material.emissiveIntensity = 1.9 * aversion * pulse
      if (state.antennalLobe) {
        state.antennalLobe.emissive.setHex(INK.quiet)
        state.antennalLobe.emissiveIntensity = 0.5 * drive
      }
      state.calyxGlow.intensity = 22 * dopamine * pulse
      renderer.render(scene, camera)
    }
    tick()

    return () => {
      disposed = true
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
  }, [circuit.kenyonCells])

  useEffect(() => {
    const state = rig.current
    if (!state) return

    state.target.dopamine = Math.min(1, frame?.dopamine ?? 0)
    state.target.aversion = Math.min(1, frame?.aversion ?? 0)
    const ear = frame?.ear ?? []
    state.target.drive = ear.length
      ? Math.min(1, ear.reduce((sum, v) => sum + v, 0) / ear.length / 0.35)
      : 0

    const colors = state.kenyonColors
    const sizes = state.kenyonSizes
    if (!colors || !sizes) return
    const quiet = new THREE.Color(INK.quiet)
    const hot = new THREE.Color(INK.kenyon)
    // Only cells that changed state are touched: repainting all 4,000 every
    // 128 ms is most of a frame's budget for no visible gain.
    for (const i of state.lit) {
      colors.setXYZ(i, quiet.r, quiet.g, quiet.b)
      sizes.setX(i, 0.055)
    }
    state.lit.clear()
    for (const i of frame?.kenyon ?? []) {
      if (i < 0 || i >= sizes.count) continue
      colors.setXYZ(i, hot.r, hot.g, hot.b)
      sizes.setX(i, 0.17)
      state.lit.add(i)
    }
    colors.needsUpdate = true
    sizes.needsUpdate = true
  }, [frame])

  return (
    <div className="brain-stage">
      <div ref={host} className="brain-host" />
      {status !== 'ready' && (
        <p className="brain-status">
          {status === 'loading' ? 'loading the hemibrain' : 'the neuropil meshes did not load'}
        </p>
      )}
      <div className="brain-hud">
        <span>
          {live
            ? `${frame?.kenyon.length ?? 0} of ${circuit.kenyonCells} Kenyon cells`
            : 'at rest'}
        </span>
        <span className="brain-hud-soft">hemibrain v1.2 &middot; drag to turn</span>
      </div>
    </div>
  )
}
