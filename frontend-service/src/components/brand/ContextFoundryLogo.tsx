import React from 'react';

interface ContextFoundryLogoProps {
  className?: string;
  showText?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export const ContextFoundryLogo: React.FC<ContextFoundryLogoProps> = ({
  className = '',
  showText = true,
  size = 'md',
}) => {
  const iconSize = size === 'sm' ? 28 : size === 'lg' ? 40 : 34;

  return (
    <div className={`flex items-center gap-2.5 select-none ${className}`}>
      {/* Geometric Foundry Cube Mark */}
      <svg
        width={iconSize}
        height={iconSize}
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0 drop-shadow-xs transition-transform duration-200 group-hover:scale-105"
      >
        <defs>
          <linearGradient id="cfOrangeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#ff7a45" />
            <stop offset="100%" stopColor="#f05a28" />
          </linearGradient>
          <linearGradient id="cfBurgundyGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#9e2a4b" />
            <stop offset="100%" stopColor="#6f152d" />
          </linearGradient>
          <linearGradient id="cfTopGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#ff9f43" />
            <stop offset="100%" stopColor="#f05a28" />
          </linearGradient>
        </defs>

        {/* Isometric Foundry Hexagon Cube */}
        {/* Top facet */}
        <polygon points="32,8 54,20 32,32 10,20" fill="url(#cfTopGrad)" />
        {/* Left facet (Burgundy / Deep Energy) */}
        <polygon points="10,23 30,34 30,56 10,45" fill="url(#cfBurgundyGrad)" />
        {/* Right facet (Warm Orange Energy) */}
        <polygon points="34,34 54,23 54,45 34,56" fill="url(#cfOrangeGrad)" />
        {/* Center node */}
        <circle cx="32" cy="33" r="3.5" fill="#ffffff" />
      </svg>

      {showText && (
        <div className="flex flex-col text-left">
          <div className="flex items-center text-slate-900 font-extrabold tracking-tight leading-none text-base md:text-lg">
            <span>Context</span>
            <span className="text-[#f05a28]">
              Foundry
            </span>
          </div>
          <span className="text-[9px] font-semibold tracking-wider text-slate-400 uppercase mt-0.5">
            Dev Central · Eng Intelligence
          </span>
        </div>
      )}
    </div>
  );
};
