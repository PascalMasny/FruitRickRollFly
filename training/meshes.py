"""Pull the real neuropil surfaces out of the hemibrain and ship them to the web.

The browser draws the mushroom body as measured anatomy rather than as shapes
we invented: the calyx the Kenyon cells actually have their dendrites in, the
peduncle their axons actually run down, and the lobes the output neurons
actually read. Those surfaces come from the Janelia FlyEM hemibrain v1.2 ROI
segmentation, which is public and CC BY 4.0.

This is a build step, not part of running the fly. Its output is committed, so
a clone needs neither the extra dependencies nor the download:

    uv pip install -e '.[meshes]'
    frrf-meshes

Hemibrain coordinates are nanometres with y running dorsal to ventral and z
running posterior to anterior. The exported frame is the one three.js wants:
micrometres, +y up, +z toward the viewer, centred on the mushroom body.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

HEMIBRAIN = "precomputed://gs://neuroglancer-janelia-flyem-hemibrain/v1.2/rois"

# Segment ids come from the source's own segment_properties. `role` is ours:
# "circuit" is a stage this model actually computes, "context" is the rest of
# the brain, drawn dim so you can see how little of the animal is in use.
ROIS: list[dict] = [
    {"id": 13, "roi": "CA(R)", "name": "calyx", "role": "circuit", "lod": 0},
    {"id": 37, "roi": "PED(R)", "name": "peduncle", "role": "circuit", "lod": 0},
    {"id": 57, "roi": "aL(R)", "name": "alpha", "role": "avoidance", "lod": 0},
    {"id": 55, "roi": "a'L(R)", "name": "alpha-prime", "role": "avoidance", "lod": 0},
    {"id": 61, "roi": "bL(R)", "name": "beta", "role": "approach", "lod": 0},
    {"id": 59, "roi": "b'L(R)", "name": "beta-prime", "role": "approach", "lod": 0},
    {"id": 63, "roi": "gL(R)", "name": "gamma", "role": "approach", "lod": 0},
    {"id": 4, "roi": "AL(R)", "name": "antennal-lobe", "role": "circuit", "lod": 0},
    {"id": 31, "roi": "LH(R)", "name": "lateral-horn", "role": "context", "lod": 1},
    {"id": 34, "roi": "ME(R)", "name": "medulla", "role": "context", "lod": 1},
    {"id": 32, "roi": "LO(R)", "name": "lobula", "role": "context", "lod": 1},
    {"id": 33, "roi": "LOP(R)", "name": "lobula-plate", "role": "context", "lod": 1},
]

# The mushroom body is what the picture is about, so it sits at the origin.
CENTRE_ON = {"calyx", "peduncle", "alpha", "beta", "gamma"}
TARGET_SPAN = 9.0
"""Longest edge of the mushroom body's own bounding box, in scene units."""


def _fetch(source: str) -> dict[str, object]:
    from cloudvolume import CloudVolume

    volume = CloudVolume(source, use_https=True, progress=False)
    out: dict[str, object] = {}
    for entry in ROIS:
        fetched = volume.mesh.get(entry["id"], lod=entry["lod"])
        mesh = list(fetched.values())[0] if isinstance(fetched, dict) else fetched
        out[entry["name"]] = mesh
        print(f"  {entry['roi']:8} {len(mesh.vertices):6d} vertices  {len(mesh.faces):6d} faces")
    return out


def _orient(vertices: np.ndarray) -> np.ndarray:
    """Hemibrain nanometres to scene micrometres, dorsal up and anterior front."""
    v = np.asarray(vertices, dtype=np.float64) / 1000.0
    return np.column_stack([v[:, 0], -v[:, 1], v[:, 2]])


def _sample_inside(mesh, count: int, seed: int) -> np.ndarray:
    """Scatter points through the calyx, rejecting anything outside the surface.

    Falls back to the voxel grid when the surface is not watertight enough for
    a containment test, which is a property of the decimated mesh rather than
    of the calyx.
    """
    rng = np.random.default_rng(seed)
    low, high = mesh.bounds
    kept: list[np.ndarray] = []
    total = 0
    while sum(len(k) for k in kept) < count and total < 60:
        batch = rng.uniform(low, high, size=(count * 4, 3))
        try:
            inside = batch[mesh.contains(batch)]
        except Exception:
            inside = np.empty((0, 3))
        if len(inside) == 0 and total > 2:
            break
        kept.append(inside)
        total += 1
    points = np.concatenate(kept) if kept else np.empty((0, 3))
    if len(points) < count:
        voxels = mesh.voxelized(pitch=float((high - low).max()) / 48).fill()
        centres = np.asarray(voxels.points)
        pick = rng.integers(0, len(centres), size=count)
        jitter = rng.uniform(-voxels.pitch[0] / 2, voxels.pitch[0] / 2, size=(count, 3))
        points = centres[pick] + jitter
    return points[:count]


OUTLINE_LOD = 2
"""The coarsest level the hemibrain publishes. For a silhouette that is not a
compromise: twenty to six hundred vertices a neuropil is exactly enough to say
*fly brain* and small enough to ship."""

MIRROR = {"ME(R)", "LO(R)", "LOP(R)", "AME(R)"}
"""The hemibrain is a partial volume with only the right optic lobes in it. A
brain with one eye does not read as a brain, so these four are mirrored across
the midline to stand in for the left ones. The mirrored half is a reflection
and not a measurement, which is why it is only ever drawn as an outline."""


def build_outline(volume, out_dir: Path, centre: np.ndarray, scale: float) -> dict:
    """A whole-brain silhouette, for the panel that draws the Kenyon cells.

    The cells alone are legible but unplaceable -- a cloud of dots could be
    anything. This is the envelope they sit in, drawn as a faint wireframe, so
    it is visible that the cloud is a calyx and the calyx is in a fly's head.

    Takes the same centring and scale the Kenyon cells were written in, so the
    cloud lands where the calyx actually is rather than in the middle of the
    head.
    """
    import trimesh

    labels = _segment_labels(volume)
    pieces: dict[str, object] = {}
    for sid, label in labels.items():
        try:
            fetched = volume.mesh.get(sid, lod=OUTLINE_LOD)
        except Exception:
            continue
        mesh = list(fetched.values())[0] if isinstance(fetched, dict) else fetched
        if len(mesh.vertices) < 4:
            continue
        pieces[label] = trimesh.Trimesh(
            vertices=_orient(mesh.vertices), faces=np.asarray(mesh.faces)
        )
    if not pieces:
        raise SystemExit("no outline meshes came back")

    # The midline, taken as the mean x of every neuropil the dataset happens to
    # have on both sides. Those pairs straddle it by definition, so their
    # average is the plane to reflect the missing optic lobes through.
    straddling = [
        name[:-3] for name in pieces if name.endswith("(L)") and f"{name[:-3]}(R)" in pieces
    ]
    if straddling:
        midline = float(np.mean([
            pieces[f"{name}{side}"].vertices[:, 0].mean()
            for name in straddling for side in ("(L)", "(R)")
        ]))
    else:
        midline = float(np.concatenate([p.vertices[:, 0] for p in pieces.values()]).max())

    # The real neuropil shapes, not their convex hulls. Hulls were tried and
    # they turn an organ into a polyhedron: every concavity that makes a brain
    # look like a brain is exactly what a hull throws away. These are the
    # measured surfaces, drawn softly enough that the internal boundaries
    # never become a wireframe tangle.
    parts = list(pieces.values())

    # And the whole thing is mirrored, because the hemibrain is a partial
    # volume: mostly one hemisphere with only slivers of the other, plus a
    # single optic lobe. Reflected, it reads as the brain it came out of.
    # Reflections are not measurements, which is why this file is only ever
    # used for an outline and never for anything the fly is scored on.
    for piece in list(parts):
        flipped = piece.copy()
        flipped.vertices[:, 0] = 2.0 * midline - flipped.vertices[:, 0]
        flipped.invert()
        parts.append(flipped)
    mirrored = sorted(pieces)

    whole = trimesh.util.concatenate(parts)
    whole.apply_translation(-centre)
    whole.apply_scale(scale)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "fly-brain-outline.glb"
    scene = trimesh.Scene()
    scene.add_geometry(whole, geom_name="brain")
    path.write_bytes(scene.export(file_type="glb"))
    print(f"wrote {path} ({path.stat().st_size / 1024:.0f} kB, {len(whole.vertices)} vertices)")
    return {
        "vertices": int(len(whole.vertices)),
        "faces": int(len(whole.faces)),
        "mirrored": mirrored,
        "midline": midline,
    }


def _segment_labels(volume) -> dict:
    import json as _json
    import urllib.request

    url = volume.meta.join(volume.meta.cloudpath, "segment_properties", "info")
    url = url.replace("gs://", "https://storage.googleapis.com/").replace("precomputed://", "")
    with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310
        info = _json.loads(response.read())
    inline = info["inline"]
    labels = next(p["values"] for p in inline["properties"] if p["id"] == "label")
    return {int(i): label for i, label in zip(inline["ids"], labels, strict=True)}


def build(out_dir: Path, mesh_dir: Path, kenyon: int, seed: int, source: str) -> dict:
    import trimesh

    print(f"fetching {len(ROIS)} neuropil surfaces from the hemibrain")
    fetched = _fetch(source)

    meshes = {
        name: trimesh.Trimesh(vertices=_orient(m.vertices), faces=np.asarray(m.faces))
        for name, m in fetched.items()
    }

    # Centre and scale on the mushroom body alone, so adding optic lobes for
    # context never moves the thing the picture is about.
    anchor = np.concatenate([meshes[n].vertices for n in CENTRE_ON if n in meshes])
    centre = (anchor.min(0) + anchor.max(0)) / 2
    scale = TARGET_SPAN / float((anchor.max(0) - anchor.min(0)).max())
    for mesh in meshes.values():
        mesh.apply_translation(-centre)
        mesh.apply_scale(scale)

    out_dir.mkdir(parents=True, exist_ok=True)
    mesh_dir.mkdir(parents=True, exist_ok=True)
    # The page draws the cells and not the surfaces, so the GLB is kept as
    # provenance -- it is where the cell positions came from, and what to load
    # if the neuropils are ever wanted back -- rather than shipped to a browser
    # that would download half a megabyte and never use it.
    scene = trimesh.Scene()
    for entry in ROIS:
        scene.add_geometry(meshes[entry["name"]], geom_name=entry["name"])
    glb = mesh_dir / "fly-brain.glb"
    glb.write_bytes(scene.export(file_type="glb"))

    print(f"scattering {kenyon} Kenyon cells inside the calyx")
    points = _sample_inside(meshes["calyx"], kenyon, seed).astype(np.float32)
    cells = out_dir / "kenyon-cells.bin"
    cells.write_bytes(points.tobytes())

    manifest = {
        "source": "Janelia FlyEM hemibrain v1.2 ROI segmentation",
        "licence": "CC BY 4.0",
        "url": "https://www.janelia.org/project-team/flyem/hemibrain",
        "space": "hemibrain, right hemisphere",
        "units": "micrometres, scaled and centred on the mushroom body",
        "orientation": "+y dorsal, +z anterior",
        "kenyonCells": int(len(points)),
        "seed": seed,
        "regions": [
            {k: entry[k] for k in ("roi", "name", "role")}
            | {"vertices": int(len(meshes[entry["name"]].vertices))}
            for entry in ROIS
        ],
    }
    (mesh_dir / "fly-brain.json").write_text(json.dumps(manifest, indent=2) + "\n")

    from cloudvolume import CloudVolume

    outline = build_outline(
        CloudVolume(source, use_https=True, progress=False), out_dir, centre, scale
    )
    manifest["outline"] = outline

    print(f"wrote {glb} ({glb.stat().st_size / 1024:.0f} kB)")
    print(f"wrote {cells} ({cells.stat().st_size / 1024:.0f} kB)")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path("web/public"),
                        help="where the Kenyon cell positions the page loads are written")
    parser.add_argument("--meshes", type=Path, default=Path("models"),
                        help="where the neuropil GLB is kept; provenance, not shipped")
    parser.add_argument("--kenyon", type=int, default=8192,
                        help="size of the Kenyon cell pool; the page takes the first N")
    parser.add_argument("--seed", type=int, default=1987)
    parser.add_argument("--source", default=HEMIBRAIN)
    args = parser.parse_args(argv)
    build(args.out, args.meshes, args.kenyon, args.seed, args.source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
