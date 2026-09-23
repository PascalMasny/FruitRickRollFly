import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import type { Circuit, Frame } from '../lib/types'

interface Props {
  circuit: Circuit
  frame: Frame | null
  live: boolean
}

/* The sixteen-colour VGA bright set, which is what a graph on a black screen
   was drawn in when this song was new -- and what the 2D timeline beside this
   panel is now drawn in. Dim blue at rest, white when a cell fires, warming to
   bright yellow as dopamine builds and to bright red if the fly is being
   pushed the other way. */
const QUIET = new THREE.Color(0x4a4a7a)
const LIT = new THREE.Color(0xffffff)
const APPROACH = new THREE.Color(0xffff55)
const AVOIDANCE = new THREE.Color(0xff5555)

const DECAY_SECONDS = 0.28
/** How long a cell keeps glowing after it stops firing.

Percepts land about eight times a second. Snapping each cell on and off at that
rate reads as flicker rather than as firing, and hides the thing worth seeing:
that the set of lit cells is almost entirely different from one percept to the
next. A short tail makes that turnover legible without inventing activity --
nothing lights up that did not fire. */

/**
 * Four thousand Kenyon cells, and nothing else.
 *
 * This view used to draw the neuropil surfaces too -- calyx, peduncle, lobes --
 * which was anatomically honest and, as a shape, unfortunate. What is worth
 * looking at was never the envelope anyway: it is that roughly two hundred
 * cells out of four thousand are firing at any instant, and that which two
 * hundred changes completely as the song moves.
 *
 * The positions are still real. They were sampled inside the hemibrain's own
 * calyx surface and rejected against the mesh, so the cloud is the shape of the
 * place these cells actually sit, even with the surface no longer drawn.
 *
 * Colour carries the pools: bone at rest, warming to amber as dopamine builds
 * and to red if the fly is being pushed the other way.
 */
export default function BrainView({ circuit, frame, live }: Props) {
  const host = useRef<HTMLDivElement>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'failed'>('loading')
  const rig = useRef<{
    colors: THREE.BufferAttribute
    sizes: THREE.BufferAttribute
    level: Float32Array
    count: number
    target: { dopamine: number; aversion: number }
    firing: number[]
    pending: boolean
  } | null>(null)

  useEffect(() => {
    const element = host.current
    if (!element) return
    let disposed = false

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 200)
    /* A browser with WebGL switched off, or a machine with no GPU to give it,
       threw here -- and with nothing catching it the whole application
       unmounted and the page went blank. The cells are the best thing on it
       and they are still not worth the verdict, so this degrades to the panel
       saying so and everything else carries on. */
    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    } catch (error) {
      console.error('kenyon cells: no WebGL', error)
      // The one render this costs is on a machine that cannot draw the panel
      // anyway, which is the event that caused the change.
      // oxlint-disable-next-line react/set-state-in-effect
      setStatus('failed')
      return
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    element.appendChild(renderer.domElement)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.06
    controls.enablePan = false
    controls.autoRotate = true
    controls.autoRotateSpeed = 0.5

    const world = new THREE.Group()
    scene.add(world)

    fetch('kenyon-cells.bin')
      .then(async (response) => {
        if (!response.ok) throw new Error(`kenyon-cells.bin: ${response.status}`)
        return new Float32Array(await response.arrayBuffer())
      })
      .then((pool) => {
        if (disposed) return
        const count = Math.min(circuit.kenyonCells, Math.floor(pool.length / 3))
        const positions = pool.slice(0, count * 3)

        const colors = new Float32Array(count * 3)
        const sizes = new Float32Array(count)
        for (let i = 0; i < count; i += 1) {
          colors[i * 3] = QUIET.r
          colors[i * 3 + 1] = QUIET.g
          colors[i * 3 + 2] = QUIET.b
          sizes[i] = 0.062
        }

        const geometry = new THREE.BufferGeometry()
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
        const colorAttr = new THREE.BufferAttribute(colors, 3)
        const sizeAttr = new THREE.BufferAttribute(sizes, 1)
        geometry.setAttribute('color', colorAttr)
        geometry.setAttribute('size', sizeAttr)

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
        world.add(points)

        /* Centred on the cells, not on the brain. The calyx really is up and
           off to one side -- that is where a mushroom body lives -- but
           framing the whole brain put the one thing worth looking at in a
           corner. The brain now sits around the cloud instead of the cloud
           sitting in the brain's margin. */
        /* Framed on the cloud alone. There is no outline to frame against any
           more: the picture is the cells firing, and everything drawn around
           them turned out to be something to see past. */
        geometry.computeBoundingSphere()
        const sphere = geometry.boundingSphere
        const reach = sphere ? sphere.radius : 3
        if (sphere) world.position.sub(sphere.center)
        camera.position.set(reach * 0.8, reach * 0.5, reach * 2.1)
        controls.target.set(0, 0, 0)
        controls.minDistance = reach * 0.8
        controls.maxDistance = reach * 6

        rig.current = {
          colors: colorAttr,
          sizes: sizeAttr,
          level: new Float32Array(count),
          count,
          target: { dopamine: 0, aversion: 0 },
          firing: [],
          pending: false,
        }
        setStatus('ready')
      })
      .catch((error) => {
        console.error('kenyon cells', error)
        if (!disposed) setStatus('failed')
      })

    /* The panel is a wide box on a desktop and a tall one on a phone, so the
       vertical angle opens up on a narrow one rather than cropping the cloud. */
    const BASE_FOV = 38
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
    const hot = new THREE.Color()
    const shade = new THREE.Color()
    const tick = () => {
      raf = requestAnimationFrame(tick)
      const dt = clock.getDelta()
      controls.update()

      const state = rig.current
      if (state) {
        const { level, colors, sizes, count, target } = state
        if (state.pending) {
          for (const i of state.firing) if (i >= 0 && i < count) level[i] = 1
          state.pending = false
        }
        // Warm the lit colour towards whichever pool is winning.
        hot.copy(LIT)
        if (target.dopamine > 0) hot.lerp(APPROACH, Math.min(1, target.dopamine))
        if (target.aversion > target.dopamine) {
          hot.lerp(AVOIDANCE, Math.min(1, target.aversion))
        }
        const keep = Math.exp(-dt / DECAY_SECONDS)
        for (let i = 0; i < count; i += 1) {
          const value = level[i]
          if (value <= 0.002) {
            if (value !== 0) {
              level[i] = 0
              colors.setXYZ(i, QUIET.r, QUIET.g, QUIET.b)
              sizes.setX(i, 0.062)
            }
            continue
          }
          level[i] = value * keep
          shade.copy(QUIET).lerp(hot, value)
          colors.setXYZ(i, shade.r, shade.g, shade.b)
          sizes.setX(i, 0.062 + 0.24 * value)
        }
        colors.needsUpdate = true
        sizes.needsUpdate = true
      }
      renderer.render(scene, camera)
    }
    tick()

    return () => {
      disposed = true
      cancelAnimationFrame(raf)
      observer.disconnect()
      controls.dispose()
      world.traverse((object) => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Points ||
            object instanceof THREE.LineSegments) {
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
    // Handed to the animation loop rather than written here: the loop owns
    // every level so the decay and the new firings cannot fight each other.
    state.firing = frame?.kenyon ?? []
    state.pending = true
  }, [frame])

  return (
    <div className="brain-stage">
      <div ref={host} className="brain-host" />
      {status !== 'ready' && (
        <p className="brain-status">
          {status === 'loading' ? 'placing the cells' : 'the Kenyon cells did not load'}
        </p>
      )}
      <div className="brain-hud">
        <span>
          {live
            ? `${frame?.kenyon.length ?? 0} of ${circuit.kenyonCells} Kenyon cells`
            : `${circuit.kenyonCells} Kenyon cells, none firing`}
        </span>
        <span className="brain-hud-soft">positions from hemibrain v1.2 &middot; drag to turn</span>
      </div>
    </div>
  )
}
