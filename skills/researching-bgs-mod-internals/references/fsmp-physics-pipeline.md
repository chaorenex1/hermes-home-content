# Faster HDT-SMP (FSMP) internals

Source-verified against `DaymareOn/hdtSMP64` main at commit `e52ad96` (Aug 2026), matching the Nexus 4.1.x line. Nexus mod 57339.

## What it is

- SKSE plugin DLL and full replacement for HDT-SMP. Lineage: HydrogensaysHDT -> aers -> Karonar1 -> DaymareOn.
- Pure CPU. The repository contains no CUDA/GPU code; the only "GPU algorithms" mention is an extension-point comment.
- Engine, not content: XML defines bones, constraints, and collision; NIF supplies the mesh and skin weights.

## Data model

- Each `<bone>` becomes a `btRigidBody`. `mass` 0 sets `CF_KINEMATIC_OBJECT` (collision anchor, never integrated); mass > 0 is dynamic.
- Shape sources: box/sphere/capsule/cylinder/compound written in XML, plus `per-vertex-shape` and `per-triangle-shape`, which are generated from the named NIF mesh.
  - per-vertex: one sphere per skinned vertex, radius = shape margin x margin-multiplier x bone scale.
  - per-triangle: one thin plate per triangle with margin and penetration tolerance, plus a companion per-vertex shape for triangle/triangle cases.
- `<generic-constraint>` maps to `btGeneric6DofSpring2Constraint`: 6-axis linear/angular springs with stiffness, damping, limits, equilibrium, motors. Also `stiff-spring` and `cone-twist`.
- Filtering: `shared` (public/internal/external/private), tag and bone allow/deny lists, `disable-tag` with `disable-priority`.
- Vertices carry 4 bone weights; the same weights decide skinning position and how contact impulses are distributed to bones.

## Frame pipeline

1. `FrameEvent` (main thread): ActorManager picks active skeletons (view, distance, cell, disable tags, `maxActiveSkeletons` budget) and removes inactive systems from the world. `readTransform` samples bone world transforms: skeleton root serial (race safety), systems in `tbb::parallel_for`.
2. `m_tasks.run(doUpdate2ndStep)` posts the simulation to a TBB task group.
3. Worker: `applyGravity` uses -9.8 x scaleSkyrim (scaleSkyrim = 1/0.01425 ~ 70.18, so ~ -688 units/s^2); `applyWind` adds multi-frequency gusts whose phase is advected by bone position and attenuated by relative velocity.
4. `stepSimulation`: tick = min(average frame interval, 1/60); at most 4 substeps; skip when the accumulated interval is under half a tick; a remainder above 1/300 s gets one variable-length step. Per substep: predict unconstrained motion -> discrete collision detection -> simulation islands -> solve constraints -> integrate transforms.
5. `FrameSync` (main thread): `m_tasks.wait()`, then `writeTransform` writes rigid-body transforms back to NiNode.

## Collision layers

- Broadphase: `btDbvtBroadphase` over one AABB per mesh, built from bone bounding spheres.
- Midphase: `ColliderTree` keyed by the vertex's bone path (up to 4 levels); each node caches `aabbMe` (own colliders) and `aabbAll` (with subtree). Kinematic subtrees are pruned. Candidate leaf pairs are capped at 6024; exceeding it abandons the pair.
- Narrowphase: analytic, no GJK/EPA. Vertex sphere vs sphere; vertex sphere vs triangle via plane distance, barycentric containment, and penetration tolerance, using SSE cross/dot products. At most 512 results per mesh pair, sorted by depth, then merged.
- Merge: weight = bone weight x `flexible` (sum of non-kinematic weights), applied as w^3 into one contact per bone pair, emitted as a `btManifoldPoint` between the two bone rigid bodies. Cloth-vs-body ultimately solves as bone-vs-bone contacts.

## Solver

- `btDiscreteDynamicsWorldMt` with `btConstraintSolverPoolMt` (one sequential-impulse solver per hardware thread), island-parallel. No `btBatchedConstraints`.
- Solver info: global `friction` 0 (contact friction = product of the two bones' friction), split impulse with threshold -0.01, `erp2` 0.15, `globalCfm` 0.001, `restitutionVelocityThreshold` 0.2, `SOLVER_SIMD`, no warm starting.
- Manifolds are cleared after every solve (`clearAllManifold`), so contacts are rebuilt each frame. Constraints whose both bodies are kinematic are disabled each solve.

## Why it is faster

1. `clipColliders` drops colliders whose bone weights are all below threshold; `finishBuild` keeps only referenced vertices and remaps them, shrinking skinning work.
2. SSE or AVX2+FMA 4-bone skinning and SSE narrowphase on 16-byte vertex data.
3. TBB across systems, mesh pairs, leaf pairs, and islands.
4. Kinematic-subtree pruning plus two-stage AABB narrowing per pair.
5. Hard caps of 512 contacts and 6024 leaf pairs.
6. Per-actor LOD: only active skeletons are in the world; `maxActiveSkeletons` auto-adjusts to a 3.5 ms budget within 3-20.
7. Build variants `noavx`/`avx`/`avx2`/`avx512` selected by `/arch` flags in `CMakePresets.json`.

## Hard limits

- Vertices are unconstrained; softness comes from 6DOF springs on the bone chain. Few bones means stiff. This is not PBD/XPBD cloth.
- Discrete collision, no CCD: fast thin plates can tunnel.
- Cap overflow drops contacts, which shows up as softness or clipping.
- Time below 1/300 s is discarded.
- No warm start and no persistent manifolds; stability depends on stiffness, damping, CFM, and contact merging.
- CPU only; the main thread still pays sampling and write-back.

## Tuning and diagnosis map

- No movement: all bones `mass` 0; NIF bone names not matching XML; XML not loaded.
- Too stiff: add bone segments, lower stiffness, add damping.
- Jitter or explosion: raise margin, clamp angular velocity, slow thin plates, review CFM/ERP.
- Clipping: raise penetration/margin, reduce collider count, check the 512/6024 caps on complex outfits.
- Validate the load order with `smp report [warnings] [gear]`.
- v4 has no MCM (SKSE Menu Framework instead) and still requires PapyrusUtil, JContainers, ConsoleUtilSSE NG.

## Code map

- `src/hdtSkyrimPhysicsWorld.cpp` — frame events, async dispatch, solver info.
- `src/hdtSkinnedMesh/hdtSkinnedMeshWorld.cpp` — stepSimulation, gravity/wind, islands, solve, manifold clear.
- `src/hdtSkinnedMesh/hdtDispatcher.cpp` — broadphase pair dispatch and mid/narrow orchestration.
- `src/hdtSkinnedMesh/hdtSkinnedMeshAlgorithm.cpp` — narrowphase checks, contact merge, manifold creation.
- `src/hdtSkinnedMesh/hdtSkinnedMeshBody.cpp` — skinning, AABB, collider clipping, vertex remap.
- `src/hdtSkinnedMesh/hdtSkinnedMeshShape.cpp` — per-vertex and per-triangle collider construction.
- `src/hdtSkinnedMesh/hdtCollider.cpp` — ColliderTree traversal and kinematic pruning.
- `src/hdtSkyrimSystem.cpp` — XML to bones, shapes, constraints.
- `src/ActorManager.cpp` — active skeleton selection, budget, system add/remove.
- `src/hdtSkyrimBone.cpp` — readTransform/writeTransform.
- `CMakePresets.json` — AVX build variants.
