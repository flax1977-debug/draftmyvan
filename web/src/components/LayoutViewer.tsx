import { Suspense, useMemo, useRef, useState } from "react";
import { Canvas, useThree, type ThreeEvent } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { assetUrl, type ProjectInstance, type VanDimensions } from "../api";

// Scale: 1000 mm = 1 Three.js unit. Project axes map to Three as
// X = width, Y = height (up), Z = length (front-back).
const MM = 1000;
const SNAP_MM = 50;

const snap = (mm: number) => Math.round(mm / SNAP_MM) * SNAP_MM;

// Van-space minimum corner (mm) for an instance, mirroring runtime/anchors.py
// (rotation-0 reference; group rotation handles rotation_deg). Right anchors
// extend in -X from x; ceiling anchors hang down from z.
function minCorner(inst: ProjectInstance): [number, number, number] {
  const { x, y, z } = inst.position_mm;
  const w = inst.module?.dimensions_mm.width ?? 0;
  const h = inst.module?.dimensions_mm.height ?? 0;
  const anchor = inst.module?.anchor ?? "floor_back_left";
  const right = anchor === "wall_right" || anchor === "ceiling_right";
  const ceiling = anchor === "ceiling_left" || anchor === "ceiling_right";
  return [right ? x - w : x, ceiling ? z - h : z, y];
}

function PlacedModule({
  inst,
  url,
  onPointerDown,
}: {
  inst: ProjectInstance;
  url: string;
  onPointerDown: (e: ThreeEvent<PointerEvent>) => void;
}) {
  const { scene } = useGLTF(url);
  const { gl } = useThree();
  const object = useMemo(() => scene.clone(true), [scene]);
  // Place the GLB's local-origin (bbox-min) corner at the anchor's van-space
  // minimum corner; Three Y = van Z (height), Three Z = van Y (length).
  const [cx, cy, cz] = minCorner(inst);
  const pos: [number, number, number] = [cx / MM, cy / MM, cz / MM];
  return (
    <group
      position={pos}
      rotation={[0, THREE.MathUtils.degToRad(inst.rotation_deg), 0]}
      onPointerDown={onPointerDown}
      onPointerOver={(e) => {
        e.stopPropagation();
        gl.domElement.style.cursor = "grab";
      }}
      onPointerOut={() => {
        gl.domElement.style.cursor = "auto";
      }}
    >
      <primitive object={object} />
    </group>
  );
}

function VanShell({ van }: { van: VanDimensions }) {
  const w = van.width / MM;
  const h = van.height / MM;
  const l = van.length / MM;
  const edges = useMemo(() => new THREE.EdgesGeometry(new THREE.BoxGeometry(w, h, l)), [w, h, l]);
  return (
    <group>
      <mesh rotation-x={-Math.PI / 2} position={[w / 2, 0, l / 2]} receiveShadow>
        <planeGeometry args={[w, l]} />
        <meshStandardMaterial color="#15171a" />
      </mesh>
      <lineSegments position={[w / 2, h / 2, l / 2]} geometry={edges}>
        <lineBasicMaterial color="#3a8a5a" />
      </lineSegments>
    </group>
  );
}

function Scene({
  van,
  instances,
  onDrag,
}: {
  van: VanDimensions;
  instances: ProjectInstance[];
  onDrag: (instanceId: string, posMm: { x: number; y: number; z: number }) => void;
}) {
  const { camera, raycaster, pointer, gl, controls } = useThree() as any;
  const [dragId, setDragId] = useState<string | null>(null);
  const grab = useRef({ x: 0, z: 0 });
  // Infinite floor plane (Y = 0), used so dragging can leave the van box.
  const plane = useMemo(() => new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), []);

  const w = van.width / MM;
  const h = van.height / MM;
  const l = van.length / MM;
  const center: [number, number, number] = [w / 2, h / 2, l / 2];

  function floorPoint(): THREE.Vector3 | null {
    raycaster.setFromCamera(pointer, camera);
    const p = new THREE.Vector3();
    return raycaster.ray.intersectPlane(plane, p) ? p : null;
  }

  function startDrag(inst: ProjectInstance, e: ThreeEvent<PointerEvent>) {
    e.stopPropagation();
    const fp = floorPoint();
    if (!fp) return;
    // Grab offset between the floor point under the cursor and the anchor.
    grab.current = { x: fp.x - inst.position_mm.x / MM, z: fp.z - inst.position_mm.y / MM };
    if (controls) controls.enabled = false; // don't orbit while dragging
    gl.domElement.style.cursor = "grabbing";
    setDragId(inst.instance_id);
  }

  function onMove(e: ThreeEvent<PointerEvent>) {
    if (!dragId) return;
    const inst = instances.find((i) => i.instance_id === dragId);
    if (!inst) return;
    // e.point is on the Y=0 catcher plane → world floor coords.
    const ax = e.point.x - grab.current.x;
    const az = e.point.z - grab.current.z;
    onDrag(dragId, { x: snap(ax * MM), y: snap(az * MM), z: inst.position_mm.z });
  }

  function endDrag() {
    if (controls) controls.enabled = true;
    gl.domElement.style.cursor = "grab";
    setDragId(null);
  }

  return (
    <>
      <color attach="background" args={["#0a0a0a"]} />
      <ambientLight intensity={0.7} />
      <directionalLight position={[5, 10, 5]} intensity={1.4} />
      <VanShell van={van} />
      <Suspense fallback={null}>
        {instances
          .filter((i) => i.visible && i.module)
          .map((inst) => (
            <PlacedModule
              key={inst.instance_id}
              inst={inst}
              url={assetUrl(inst.module!.glb_url)}
              onPointerDown={(e) => startDrag(inst, e)}
            />
          ))}
      </Suspense>
      {/* Invisible catcher plane active only while dragging, so moves track
          the pointer even past the van box. */}
      {dragId && (
        <mesh
          rotation-x={-Math.PI / 2}
          position={[0, 0, 0]}
          onPointerMove={onMove}
          onPointerUp={endDrag}
          onPointerLeave={endDrag}
        >
          <planeGeometry args={[1000, 1000]} />
          <meshBasicMaterial transparent opacity={0} depthWrite={false} />
        </mesh>
      )}
      <OrbitControls makeDefault enableDamping enabled={!dragId} target={center} />
    </>
  );
}

export default function LayoutViewer({
  van,
  instances,
  onDrag,
}: {
  van: VanDimensions;
  instances: ProjectInstance[];
  onDrag: (instanceId: string, posMm: { x: number; y: number; z: number }) => void;
}) {
  const w = van.width / MM;
  const h = van.height / MM;
  const l = van.length / MM;
  const dist = Math.max(w, l, h);
  const camPos: [number, number, number] = [w / 2 + dist * 0.9, h + dist * 0.9, l + dist * 0.6];

  return (
    <Canvas camera={{ position: camPos, fov: 45, near: 0.1, far: 1000 }} dpr={[1, 2]}>
      <Scene van={van} instances={instances} onDrag={onDrag} />
    </Canvas>
  );
}
