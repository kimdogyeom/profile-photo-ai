import React from 'react';
import './Logo.css';

export const Logo = ({ size = 'medium', variant = 'full' }) => {
  const sizes = {
    small: { icon: 24, text: 16 },
    medium: { icon: 32, text: 20 },
    large: { icon: 48, text: 28 },
    xlarge: { icon: 64, text: 36 }
  };

  const currentSize = sizes[size];

  // Icon only
  if (variant === 'icon') {
    return (
      <div className="logo-container">
        <LogoIcon size={currentSize.icon} />
      </div>
    );
  }

  // Full logo with text
  return (
    <div className="logo-container">
      <LogoIcon size={currentSize.icon} />
      {variant === 'full' && (
        <span className="logo-text" style={{ fontSize: `${currentSize.text}px` }}>
          ProfilePhotoAI
        </span>
      )}
    </div>
  );
};

// Logo icon component
const LogoIcon = ({ size }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 48 48"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className="logo-icon"
  >
    {/* Outer circle - camera lens */}
    <circle
      cx="24"
      cy="24"
      r="20"
      stroke="url(#gradient1)"
      strokeWidth="2"
      fill="none"
    />

    {/* Middle circle */}
    <circle
      cx="24"
      cy="24"
      r="14"
      stroke="url(#gradient1)"
      strokeWidth="1.5"
      fill="none"
      opacity="0.6"
    />

    {/* Inner circle - lens center */}
    <circle
      cx="24"
      cy="24"
      r="8"
      fill="url(#gradient2)"
    />

    {/* AI sparkle effects */}
    <g className="sparkles">
      {/* Top sparkle */}
      <path
        d="M24 4 L25 7 L28 8 L25 9 L24 12 L23 9 L20 8 L23 7 Z"
        fill="url(#gradient1)"
      />

      {/* Right sparkle */}
      <path
        d="M40 18 L40.5 19.5 L42 20 L40.5 20.5 L40 22 L39.5 20.5 L38 20 L39.5 19.5 Z"
        fill="url(#gradient1)"
        opacity="0.8"
      />

      {/* Bottom left sparkle */}
      <path
        d="M10 32 L10.5 33.5 L12 34 L10.5 34.5 L10 36 L9.5 34.5 L8 34 L9.5 33.5 Z"
        fill="url(#gradient1)"
        opacity="0.8"
      />
    </g>

    {/* Gradient definitions */}
    <defs>
      <linearGradient id="gradient1" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#667eea" />
        <stop offset="100%" stopColor="#764ba2" />
      </linearGradient>
      <linearGradient id="gradient2" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#667eea" stopOpacity="0.8" />
        <stop offset="100%" stopColor="#764ba2" stopOpacity="0.9" />
      </linearGradient>
    </defs>
  </svg>
);

export default Logo;
