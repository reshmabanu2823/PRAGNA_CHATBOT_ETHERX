import { useEffect, useRef } from "react";

export default function useAutoScroll(deps) {
  const ref = useRef(null);

  useEffect(() => {
    if (ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight;
    }
  }, deps);

  return ref;
}
