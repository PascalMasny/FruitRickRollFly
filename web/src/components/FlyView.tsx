import { useEffect, useRef } from 'react'
import * as THREE from 'three'

interface Props {
  video: HTMLVideoElement | null
  /** Dopamine, 0..1. The fly leans in when it starts to recognise the song. */
  dopamine: number
  committed: boolean
  /** Whether the video is actually running. Nothing moves when it is not. */
  playing: boolean
}

const CHITIN = 0xb08850
const CHITIN_DARK = 0x6b4f26
const EYE = 0xb3121f
const WING_REST = 0.62
// Wings held a little above flat, so the screen has something to catch.

/**
 * A fly, sitting in front of a screen, watching whatever was pasted in.
 *
 * The screen is a texture of the same `<video>` element the panel above plays,
 * not a second copy: one download, one decode, and the two can never drift
 * apart because they are the same element.
 *
 * It is a cartoon and says so -- the measured anatomy is next door in the
 * Kenyon cell view. What it is honest about is scale and attention: the animal
 * doing this work is a few millimetres of insect, and it leans towards the
 * screen as its dopamine rises.
 */
export default function FlyView({ video, dopamine, committed, playing }: Props) {
  const host = useRef<HTMLDivElement>(null)
  const rig = useRef<{
    fly: THREE.Group
    screen: THREE.Mesh
    glow: THREE.PointLight
    wings: THREE.Group[]
    staticMaterial: THREE.ShaderMaterial
    screenMaterial: THREE.MeshBasicMaterial
    live: boolean
    target: { dopamine: number; committed: boolean; playing: boolean }
  } | null>(null)

  useEffect(() => {
    const element = host.current
    if (!element) return

    const scene = new THREE.Scene()
    /* The panel is a wide letterbox, so the shot is staged across it rather
       than into it: the fly in profile on the left, the screen angled in on
       the right, and both readable at once. */
    const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100)
    camera.position.set(0.1, 0.8, 5.9)
    camera.lookAt(0.15, 0.1, 0)

    /* As in BrainView: without WebGL this threw, and an uncaught throw in an
       effect takes the whole tree with it. The fly is decoration. */
    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    } catch (error) {
      console.error('the animal: no WebGL', error)
      return
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.25
    element.appendChild(renderer.domElement)

    /* Lit almost entirely by the monitor, which is the point of the picture:
       the only light in the room is the thing it is watching. A little cold
       ambient keeps the far side of the animal from going to pure black. */
    scene.add(new THREE.AmbientLight(0x9fb0c4, 0.55))
    const rim = new THREE.DirectionalLight(0x8fa6c0, 0.55)
    rim.position.set(-5, 3, 2)
    scene.add(rim)
    const key = new THREE.DirectionalLight(0xffdca8, 1.1)
    key.position.set(4, 2, 2)
    scene.add(key)

    /* ── the screen ─────────────────────────────────────────────────────────
       With nothing pasted in there is nothing to watch, and a black rectangle
       does not say that -- it says broken. So the monitor carries no signal
       the way a monitor with no input does: snow, scanlines, and a roll bar
       working its way down. */
    const staticMaterial = new THREE.ShaderMaterial({
      uniforms: { uTime: { value: 0 } },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform float uTime;
        varying vec2 vUv;

        float hash(vec2 p) {
          return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
        }

        void main() {
          // Quantised in time so the snow crawls at a believable rate rather
          // than strobing at whatever the display happens to run at.
          float frame = floor(uTime * 18.0);
          float snow = hash(floor(vUv * vec2(220.0, 130.0)) + frame);
          snow = 0.26 + 0.5 * snow;

          float scan = 0.86 + 0.14 * sin(vUv.y * 420.0);
          float roll = fract(vUv.y + uTime * 0.13);
          float bar = smoothstep(0.0, 0.06, roll) * smoothstep(0.22, 0.14, roll);
          vec3 colour = vec3(snow * scan) * (0.4 + 0.5 * bar);

          // A vignette, so it reads as a tube and not as a texture.
          vec2 d = vUv - 0.5;
          colour *= 1.0 - 0.9 * dot(d, d);
          gl_FragColor = vec4(colour * vec3(0.82, 0.86, 1.0), 1.0);
        }
      `,
    })
    const screenMaterial = new THREE.MeshBasicMaterial({ color: 0x0b0b0b })
    const monitor = new THREE.Group()

    /* A CRT, which means a tube: the picture sits on a bulged glass face, the
       cabinet tapers back towards the neck, and the whole thing is deep
       rather than flat. Four to three, because a set this shape never was
       anything else. */
    const glass = new THREE.PlaneGeometry(2.5, 1.88, 14, 11)
    const vertices = glass.attributes.position
    for (let i = 0; i < vertices.count; i += 1) {
      const u = vertices.getX(i) / 1.25
      const v = vertices.getY(i) / 0.94
      vertices.setZ(i, 0.2 * (1 - 0.55 * u * u - 0.55 * v * v))
    }
    glass.computeVertexNormals()
    const screen = new THREE.Mesh(glass, staticMaterial)
    screen.position.set(0, 0.95, 0.12)
    monitor.add(screen)

    const caseMaterial = new THREE.MeshStandardMaterial({
      color: 0x2b2722, roughness: 0.75, metalness: 0.05, flatShading: true,
    })
    const bezel = new THREE.Mesh(new THREE.BoxGeometry(2.96, 2.34, 0.34), caseMaterial)
    bezel.position.set(0, 0.95, -0.06)
    monitor.add(bezel)
    const tube = new THREE.Mesh(new THREE.CylinderGeometry(1.5, 0.62, 1.9, 4), caseMaterial)
    tube.rotation.set(Math.PI / 2, Math.PI / 4, 0)
    tube.position.set(0, 0.95, -1.18)
    monitor.add(tube)

    const knobMaterial = new THREE.MeshStandardMaterial({
      color: 0x100e0c, roughness: 0.6, flatShading: true,
    })
    for (let i = 0; i < 2; i += 1) {
      const knob = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 0.1, 6), knobMaterial)
      knob.rotation.x = Math.PI / 2
      knob.position.set(1.2, 0.42 - i * 0.3, 0.12)
      monitor.add(knob)
    }

    const feet = new THREE.Mesh(new THREE.BoxGeometry(2.5, 0.16, 1.8), caseMaterial)
    feet.position.set(0, -0.3, -0.5)
    monitor.add(feet)
    monitor.position.set(1.85, -0.2, -0.5)
    monitor.rotation.y = -0.62
    scene.add(monitor)

    // The screen is the only real light in the room, which is what watching
    // something in the dark looks like.
    const glow = new THREE.PointLight(0xffe8c0, 14, 16, 2)
    glow.position.set(0.9, 0.9, 0.6)
    scene.add(glow)

    // ── the fly ─────────────────────────────────────────────────────────────
    const fly = new THREE.Group()
    // Low poly throughout: few facets and flat shading, so every surface is
    // a plane you can see the edge of. An insect is the right subject for it
    // -- it is chitin plates all the way down.
    const shell = (colour: number, rough = 0.45) =>
      new THREE.MeshStandardMaterial({
        color: colour, roughness: rough, metalness: 0.25, flatShading: true,
      })

    const abdomen = new THREE.Mesh(new THREE.IcosahedronGeometry(0.46, 0), shell(CHITIN_DARK))
    abdomen.scale.set(0.78, 0.72, 1.55)
    abdomen.position.set(0, 0, 0.62)
    fly.add(abdomen)
    // The bands a Drosophila abdomen actually has.
    for (let i = 0; i < 3; i += 1) {
      const band = new THREE.Mesh(new THREE.TorusGeometry(0.3 - i * 0.03, 0.04, 3, 8), shell(0x3a2a14))
      band.rotation.y = Math.PI / 2
      band.position.set(0, 0.02, 0.38 + i * 0.26)
      fly.add(band)
    }

    const thorax = new THREE.Mesh(new THREE.IcosahedronGeometry(0.42, 0), shell(CHITIN))
    thorax.scale.set(1.0, 0.95, 1.1)
    fly.add(thorax)

    const head = new THREE.Mesh(new THREE.IcosahedronGeometry(0.32, 0), shell(0xa07a44))
    head.position.set(0, 0.1, -0.44)
    fly.add(head)

    // Red compound eyes, which on a fly are most of the head.
    // A compound eye is a lattice of facets, so a low-poly sphere is not a
    // simplification here -- it is closer to the thing than a smooth one.
    const eyeMaterial = new THREE.MeshStandardMaterial({
      color: EYE, roughness: 0.3, metalness: 0.1, emissive: EYE,
      emissiveIntensity: 0.18, flatShading: true,
    })
    for (const side of [-1, 1]) {
      const eye = new THREE.Mesh(new THREE.IcosahedronGeometry(0.25, 0), eyeMaterial)
      eye.position.set(side * 0.2, 0.13, -0.45)
      eye.scale.set(0.9, 1.05, 1.0)
      fly.add(eye)
    }
    for (const side of [-1, 1]) {
      const arista = new THREE.Mesh(
        new THREE.CylinderGeometry(0.014, 0.004, 0.34, 3),
        shell(0x2a2018, 0.9),
      )
      arista.position.set(side * 0.09, 0.3, -0.58)
      arista.rotation.set(-0.5, 0, side * 0.4)
      fly.add(arista)
    }

    const wings: THREE.Group[] = []
    const wingMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xd8e6f6, transparent: true, opacity: 0.62, roughness: 0.1,
      transmission: 0.5, side: THREE.DoubleSide
    })
    for (const side of [-1, 1]) {
      /* Hinged on top of the thorax and swept back over the abdomen, which is
         where a fly keeps them at rest. The sweep lives on the pivot's y and
         the beat on its x, so the flap cannot fight the resting pose. */
      const pivot = new THREE.Group()
      pivot.position.set(side * 0.13, 0.22, 0.12)
      pivot.rotation.set(WING_REST, -0.95, 0)
      pivot.scale.x = side

      // An explicit six-sided wing rather than a subdivided curve: at this
      // facet count a bezier collapses into a sliver, and a flat polygon is
      // what low poly means anyway.
      const shape = new THREE.Shape()
      shape.moveTo(0, 0)
      shape.lineTo(0.3, 0.26)
      shape.lineTo(0.78, 0.24)
      shape.lineTo(1.05, 0.02)
      shape.lineTo(0.72, -0.19)
      shape.lineTo(0.28, -0.17)
      shape.closePath()
      const wing = new THREE.Mesh(new THREE.ShapeGeometry(shape), wingMaterial)
      wing.rotation.x = -Math.PI / 2
      wing.scale.setScalar(0.92)
      pivot.add(wing)

      // An outline, because a transparent membrane seen nearly edge-on in a
      // dark room is otherwise not there at all.
      const outline = new THREE.LineLoop(
        new THREE.BufferGeometry().setFromPoints(shape.getPoints()),
        new THREE.LineBasicMaterial({ color: 0xbcd2e8, transparent: true, opacity: 0.55 }),
      )
      outline.rotation.x = -Math.PI / 2
      outline.scale.setScalar(0.92)
      pivot.add(outline)

      fly.add(pivot)
      wings.push(pivot)
    }

    const legMaterial = shell(0x2f2415, 0.85)
    for (const side of [-1, 1]) {
      for (let i = 0; i < 3; i += 1) {
        const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.026, 0.012, 0.62, 3), legMaterial)
        leg.position.set(side * 0.34, -0.3, -0.24 + i * 0.32)
        leg.rotation.set(0.25 - i * 0.22, 0, side * (0.75 + i * 0.08))
        fly.add(leg)
      }
    }

    // Facing the monitor across the frame, and a little larger than life so
    // it survives a panel this short.
    fly.scale.setScalar(1.45)
    const perch = new THREE.Vector3(-1.5, -0.25, 0.5)
    fly.position.copy(perch)
    /* Aimed at the monitor rather than eyeballed. The fly's front is its
       local -z, so the heading is taken from the vector to the screen instead
       of a hand-tuned angle that was, in fact, wrong by forty degrees. */
    const facing = new THREE.Vector3().subVectors(monitor.position, perch)
    fly.rotation.y = Math.atan2(-facing.x, -facing.z)
    scene.add(fly)

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(24, 24),
      new THREE.MeshStandardMaterial({ color: 0x0d0b09, roughness: 0.95 }),
    )
    floor.rotation.x = -Math.PI / 2
    floor.position.y = -0.92
    scene.add(floor)

    const state = {
      fly, screen, glow, wings, staticMaterial, screenMaterial,
      live: false,
      target: { dopamine: 0, committed: false, playing: false },
    }
    rig.current = state

    const resize = () => {
      const { clientWidth: w, clientHeight: h } = element
      if (w === 0 || h === 0) return
      renderer.setSize(w, h, false)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
    }
    const observer = new ResizeObserver(resize)
    observer.observe(element)
    resize()

    const lean = facing.clone().normalize().multiplyScalar(0.55)

    let raf = 0
    const clock = new THREE.Clock()
    const tick = () => {
      raf = requestAnimationFrame(tick)
      const t = clock.getElapsedTime()
      const { dopamine: da, committed: sure, playing: running } = state.target

      // Leans towards the screen as the pool fills, and its wings go when it
      // is certain. A fly that likes something does not sit still.
      // Leans along its own line of sight towards the monitor.
      /* Still unless something is playing. An animal bobbing at a dead
         screen reads as restless, or as a glitch; attention is the thing
         being drawn here, and attention has an object. Leaning in moves
         along its own line of sight rather than along x. */
      const alive = running ? 1 : 0
      state.fly.position.x = perch.x + lean.x * da * alive
      state.fly.position.z = perch.z + lean.z * da * alive
      state.fly.position.y = perch.y + 0.03 * Math.sin(t * 2.2) * alive
      state.fly.rotation.z = 0.05 * Math.sin(t * 1.7) * (0.3 + da) * alive
      // Still until it is sure. A fly that is merely suspicious sits there;
      // the wings are what it does about a Rickroll, so they are reserved for
      // one rather than spent on the approach.
      const beat = sure && running ? 26 : 0
      const amplitude = sure && running ? 0.5 : 0
      const flap = WING_REST + Math.sin(t * beat) * amplitude
      state.wings[0].rotation.x = flap
      state.wings[1].rotation.x = flap
      // An untuned screen flickers; a playing one does not.
      state.glow.intensity = state.live ? 5 + 3 * da : 2.6 + 0.6 * Math.sin(t * 9.0)
      if (!state.live) state.staticMaterial.uniforms.uTime.value = t

      renderer.render(scene, camera)
    }
    tick()

    return () => {
      cancelAnimationFrame(raf)
      observer.disconnect()
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose()
          const material = object.material
          if (Array.isArray(material)) material.forEach((m) => m.dispose())
          else material.dispose()
        }
      })
      staticMaterial.dispose()
      screenMaterial.dispose()
      renderer.dispose()
      renderer.domElement.remove()
      rig.current = null
    }
  }, [])

  // The screen shows the same element the panel plays, so they cannot drift.
  useEffect(() => {
    const state = rig.current
    if (!state) return
    if (!video) {
      state.screen.material = state.staticMaterial
      state.live = false
      return
    }
    const texture = new THREE.VideoTexture(video)
    texture.colorSpace = THREE.SRGBColorSpace
    state.screenMaterial.map = texture
    state.screenMaterial.color.setHex(0xffffff)
    state.screenMaterial.needsUpdate = true
    state.screen.material = state.screenMaterial
    state.live = true
    return () => {
      texture.dispose()
      state.screenMaterial.map = null
      state.screen.material = state.staticMaterial
      state.live = false
    }
  }, [video])

  useEffect(() => {
    const state = rig.current
    if (!state) return
    state.target.dopamine = Math.max(0, Math.min(1, dopamine))
    state.target.committed = committed
    state.target.playing = playing
  }, [dopamine, committed, playing])

  return <div ref={host} className="fly-host" />
}
