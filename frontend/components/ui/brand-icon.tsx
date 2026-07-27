"use client";

import React from "react";

export function BrandIcon({ className = "w-full h-full" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      shapeRendering="geometricPrecision"
    >
      <defs>
        <radialGradient id="crowscap-green-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#6ff16f" stopOpacity="0.95" />
          <stop offset="55%" stopColor="#42d64c" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#42d64c" stopOpacity="0" />
        </radialGradient>
        <filter id="crowscap-dot-softness" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="0.55" />
        </filter>
      </defs>

      <path
        d="M70.5 16.5C56.4 8.9 38.6 10.2 25.7 20.7C8.9 34.3 5.9 59.2 19 76.5C23.7 82.7 29.9 87.6 37 90.6"
        stroke="#050505"
        strokeWidth="12"
        strokeLinecap="round"
      />
      <circle cx="50" cy="50" r="8.3" fill="#050505" />
      <circle cx="63.2" cy="83.8" r="6.3" fill="#050505" />
      <circle cx="77.2" cy="70.4" r="4.6" fill="#050505" />
      <circle cx="85.7" cy="54.1" r="3.3" fill="#050505" />
      <circle cx="89" cy="38.4" r="2.2" fill="#050505" />
      <circle cx="78.3" cy="22.4" r="12.5" fill="url(#crowscap-green-glow)" />
      <circle
        cx="78.3"
        cy="22.4"
        r="6.7"
        fill="#4bd84f"
        filter="url(#crowscap-dot-softness)"
      />
      <circle cx="78.3" cy="22.4" r="5.7" fill="#53e45b" />
    </svg>
  );
}
