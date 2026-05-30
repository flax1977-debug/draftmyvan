import { Suspense, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { assetUrl, type ProjectInstance, type VanDimensions } from "../api";

// Scale: 1000 mm = 1 Three.js unit (i.e. millimetres / 1000 = metres). Module
// GLBs are authored in metres, so they drop in at native size. Project axes
// map to Three as X = width, Y = height (up), Z = length (front-back).
const MM = 1000;

function PlacedModule({ inst, url }: { inst: ProjectInstance; url: string }) {
  const { scene } = useGLTF(url);
  // Clone so repeated module_ids each get their own object in the graph.
  const object = useMemo(() => scene.clone(true), [scene]);
  const pos: [number, number, number] = [
    inst.position_mm.x / MM,
    inst.position_mm.z / MM,
    inst.position_mm.y / MM,
  ];
  return (
    <group position={pos} rotation={[0, THREE.MathUtils.degToRad(inst.rotation_deg), 0]}>
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
      {/* Floor plane spanning the van footprint (X x Z). */}
      <mesh rotation-x={-Math.PI / 2} position={[w / 2, 0, l / 2]} receiveShadow>
        <planeGeometry args={[w, l]} />
        <meshStandardMaterial color="#15171a" />
      </mesh>
      {/* Wireframe van bounding box. */}
      <lineSegments position={[w / 2, h / 2, l / 2]} geometry={edges}>
        <lineBasicMaterial color="#3a8a5a" />
      </lineSegments>
    </group>
  );
}

export default function LayoutViewer({
  van,
  instances,
}: {
  van: VanDimensions;
  instances: ProjectInstance[];
}) {
  const w = van.width / MM;
  const h = van.height / MM;
  const l = van.length / MM;
  const center: [number, number, number] = [w / 2, h / 2, l / 2];
  const dist = Math.max(w, l, h);
  const camPos: [number, number, number] = [w / 2 + dist * 0.9, h + dist * 0.9, l + dist * 0.6];

  return (
    <Canvas camera={{ position: camPos, fov: 45, near: 0.1, far: 1000 }} dpr={[1, 2]}>
      <color attach="background" args={["#0a0a0a"]} />
      <ambientLight intensity={0.7} />
      <directionalLight position={[5, 10, 5]} intensity={1.4} />
      <VanShell van={van} />
      <Suspense fallback={null}>
        {instances
          .filter((i) => i.visible && i.module)
          .map((inst) => (
            <PlacedModule key={inst.instance_id} inst={inst} url={assetUrl(inst.module!.glb_url)} />
          ))}
      </Suspense>
      <OrbitControls makeDefault enableDamping target={center} />
    </Canvas>
  );
}
