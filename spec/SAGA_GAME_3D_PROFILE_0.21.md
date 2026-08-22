# Saga Portable 3D Preview 0.21

Saga 0.21.0 adds a dependency-light CPU 3D baseline on top of the portable RGBA8 framebuffer.

APIs:

- `mesh3d_cube(size)`
- `mesh3d(flat_vertices, triangle_indices)`
- `mesh3d_obj(path)` with polygon fan triangulation and positive/negative OBJ vertex indices
- translate / rotate (radians) / scale
- perspective `camera3d`
- filled `draw_mesh3d`
- `draw_wireframe3d`

The renderer performs camera look-at projection, triangle rasterization, and a per-pixel depth buffer with reciprocal-depth interpolation. This makes simple software-rendered 3D games, visualizers, test scenes and asset tooling practical without requiring a GPU API.

Deliberate limits: no material system, skeletal animation, texture coordinates, perspective-correct attribute interpolation, near-plane polygon clipping, scene graph, PBR, spatial acceleration, GPU mesh pipeline or AAA engine claim. Those remain future 3D profile work.
