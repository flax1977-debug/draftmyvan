import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { Center, OrbitControls, useGLTF } from "@react-three/drei";

// Loads a GLB by URL and renders it with orbit controls. The committed asset
// is currently a placeholder box; this proves the manifest's glb_path flows
// through the API into the browser 3D view.

function Model({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  return <primitive object={scene} />;
}

export default function ModelViewer({ url }: { url: string }) {
  return (
    <Canvas camera={{ position: [2, 1.6, 2.4], fov: 45 }} dpr={[1, 2]}>
      <color attach="background" args={["#0a0a0a"]} />
      <ambientLight intensity={0.7} />
      <directionalLight position={[5, 10, 5]} intensity={1.4} />
      <gridHelper args={[10, 10, "#333", "#222"]} />
      <Suspense fallback={null}>
        <Center>
          <Model url={url} />
        </Center>
      </Suspense>
      <OrbitControls makeDefault enableDamping />
    </Canvas>
  );
}
