"use client";

import React from "react";

export function BrandIcon({ className = "w-full h-full" }: { className?: string }) {
  return (
    <svg
      viewBox="8 8 88 84"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      shapeRendering="geometricPrecision"
    >
      <defs>
        <linearGradient
          id="crescent-grad"
          x1="50"
          y1="15"
          x2="50"
          y2="85"
          gradientUnits="userSpaceOnUse"
        >
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="100%" stopColor="#8b5cf6" />
        </linearGradient>
        <radialGradient id="glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#c4b5fd" stopOpacity="0.8" />
          <stop offset="100%" stopColor="#c4b5fd" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* Glow behind top right dot */}
      <circle cx="80.3" cy="32.5" r="14" fill="url(#glow)" />
      
      {/* Top right glowing dot */}
      <circle cx="80.3" cy="32.5" r="4.5" fill="#ffffff" />

      {/* Center dot */}
      <circle cx="50" cy="50" r="7.5" fill="#ffffff" />

      {/* Trailing dots */}
      <circle cx="85" cy="50" r="1.5" fill="#ddd6fe" />
      <circle cx="80.3" cy="67.5" r="2.5" fill="#c4b5fd" />
      <circle cx="67.5" cy="80.3" r="3.5" fill="#a78bfa" />
      <circle cx="50" cy="85" r="4.5" fill="#8b5cf6" />

      {/* Crescent */}
      <path
        d="M 59 16.2 A 35 35 0 0 0 32.5 80.3"
        stroke="url(#crescent-grad)"
        strokeWidth="11.5"
        strokeLinecap="round"
      />
    </svg>
  );
}
