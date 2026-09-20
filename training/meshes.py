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
