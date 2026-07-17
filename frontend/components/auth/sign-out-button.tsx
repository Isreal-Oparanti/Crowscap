"use client";

import { LogOut } from "lucide-react";
import { signOut } from "next-auth/react";

export function SignOutButton() {
  return (
    <button
      type="button"
      onClick={() => signOut({ callbackUrl: "/" })}
      className="ml-auto flex size-8 items-center justify-center rounded-md text-[#777b7e] transition hover:bg-white hover:text-[#111111]"
      aria-label="Sign out"
      title="Sign out"
    >
      <LogOut size={15} />
    </button>
  );
}
