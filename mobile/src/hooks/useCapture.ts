import { useState } from "react";
import { captureText } from "@/api/captures";
import type { CaptureResponse } from "@/types/api";

export function useCapture() {
  const [working, setWorking] = useState(false);
  const [result, setResult] = useState<CaptureResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function capture(payload: {
    content: string;
    intent_text?: string;
    user_note?: string;
    source_title?: string;
  }): Promise<CaptureResponse | null> {
    setWorking(true);
    setError(null);
    try {
      const res = await captureText(payload);
      setResult(res);
      return res;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Capture failed.";
      setError(msg);
      return null;
    } finally {
      setWorking(false);
    }
  }

  function reset() {
    setResult(null);
    setError(null);
  }

  return { capture, working, result, error, reset };
}
