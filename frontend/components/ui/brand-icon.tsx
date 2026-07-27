"use client";

export function BrandIcon({ className = "w-full h-full" }: { className?: string }) {
  return (
    <img
      src="/icons/crowscap-icon-192.png"
      alt=""
      aria-hidden="true"
      className={`select-none object-contain ${className}`}
      draggable={false}
    />
  );
}
