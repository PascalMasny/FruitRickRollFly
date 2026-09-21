import { useEffect, useRef } from 'react'
import * as THREE from 'three'

interface Props {
  video: HTMLVideoElement | null
  /** Dopamine, 0..1. The fly leans in when it starts to recognise the song. */
  dopamine: number
  committed: boolean
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
export default function FlyView({ video, dopamine, committed }: Props) {
  const host = useRef<HTMLDivElement>(null)
  const rig = useRef<{
    fly: THREE.Group
    screen: THREE.Mesh
    glow: THREE.PointLight
    wings: THREE.Group[]
    target: { dopamine: number; committed: boolean }
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

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
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

    // ── the screen ──────────────────────────────────────────────────────────
    const screenMaterial = new THREE.MeshBasicMaterial({ color: 0x0b0b0b })
    const monitor = new THREE.Group()
    const screen = new THREE.Mesh(new THREE.PlaneGeometry(3.1, 1.74), screenMaterial)
    screen.position.y = 0.95
    monitor.add(screen)
    const bezel = new THREE.Mesh(
      new THREE.PlaneGeometry(3.32, 1.98),
      new THREE.MeshBasicMaterial({ color: 0x17130f }),
    )
    bezel.position.set(0, 0.95, -0.02)
    monitor.add(bezel)
    const stand = new THREE.Mesh(
      new THREE.CylinderGeometry(0.05, 0.3, 0.42, 5),
      new THREE.MeshStandardMaterial({ color: 0x1d1a16, roughness: 0.7 }),
    )
    stand.position.set(0, -0.2, -0.05)
    monitor.add(stand)
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
      fly, screen, glow, wings,
      target: { dopamine: 0, committed: false },
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
      const { dopamine: da, committed: sure } = state.target

      // Leans towards the screen as the pool fills, and its wings go when it
      // is certain. A fly that likes something does not sit still.
      // Leans along its own line of sight towards the monitor.
      // Leaning in means moving along its own line of sight, not along x.
      state.fly.position.x = perch.x + lean.x * da
      state.fly.position.z = perch.z + lean.z * da
      state.fly.position.y = perch.y + 0.03 * Math.sin(t * 2.2)
      state.fly.rotation.z = 0.05 * Math.sin(t * 1.7) * (0.3 + da)
      // Still until it is sure. A fly that is merely suspicious sits there;
      // the wings are what it does about a Rickroll, so they are reserved for
      // one rather than spent on the approach.
      const beat = sure ? 26 : 0
      const amplitude = sure ? 0.5 : 0
      const flap = WING_REST + Math.sin(t * beat) * amplitude
      state.wings[0].rotation.x = flap
      state.wings[1].rotation.x = flap
      state.glow.intensity = 5 + 3 * da

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
      renderer.dispose()
      renderer.domElement.remove()
      rig.current = null
    }
  }, [])

  // The screen shows the same element the panel plays, so they cannot drift.
  useEffect(() => {
    const state = rig.current
    if (!state) return
    const material = state.screen.material as THREE.MeshBasicMaterial
    if (!video) {
      material.map = null
      material.color.setHex(0x0b0b0b)
      material.needsUpdate = true
      return
    }
    const texture = new THREE.VideoTexture(video)
    texture.colorSpace = THREE.SRGBColorSpace
    material.map = texture
    material.color.setHex(0xffffff)
    material.needsUpdate = true
    return () => texture.dispose()
  }, [video])

  useEffect(() => {
    const state = rig.current
    if (!state) return
    state.target.dopamine = Math.max(0, Math.min(1, dopamine))
    state.target.committed = committed
  }, [dopamine, committed])

  return <div ref={host} className="fly-host" />
}
