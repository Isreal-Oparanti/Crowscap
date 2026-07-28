import { useAuthContext } from "@/auth/context";

/** Convenience hook — reads from AuthContext. */
export function useAuth() {
  return useAuthContext();
}
