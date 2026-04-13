import { useRef, useState } from "react";

export default function useRecorder() {
  const mediaRecorder = useRef(null);
  const chunks = useRef([]);
  const [recording, setRecording] = useState(false);

  const start = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder.current = new MediaRecorder(stream);
    chunks.current = [];

    mediaRecorder.current.ondataavailable = (e) => {
      chunks.current.push(e.data);
    };

    mediaRecorder.current.start();
    setRecording(true);
  };

  const stop = () =>
    new Promise((resolve) => {
      mediaRecorder.current.onstop = () => {
        const blob = new Blob(chunks.current, { type: "audio/webm" });
        setRecording(false);
        resolve(blob);
      };
      mediaRecorder.current.stop();
    });

  return { start, stop, recording };
}
