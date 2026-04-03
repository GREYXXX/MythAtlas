import { useEffect, useState } from "react";

export function useElementSize<T extends HTMLElement>() {
  const [node, setNode] = useState<T | null>(null);
  const [size, setSize] = useState({ width: 800, height: 600 });

  useEffect(() => {
    if (!node) return;
    const ro = new ResizeObserver(() => {
      setSize({ width: node.clientWidth, height: node.clientHeight });
    });
    ro.observe(node);
    setSize({ width: node.clientWidth, height: node.clientHeight });
    return () => ro.disconnect();
  }, [node]);

  return { ref: setNode, size };
}
