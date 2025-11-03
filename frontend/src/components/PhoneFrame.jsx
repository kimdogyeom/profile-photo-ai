import React from 'react';
import './PhoneFrame.css';

export const PhoneFrame = ({ children }) => {
  return (
    <div className="phone-frame-container">
      <div className="phone-frame">
        {/* Power button */}
        <div className="phone-button power-button"></div>

        {/* Volume buttons */}
        <div className="phone-button volume-button volume-up"></div>
        <div className="phone-button volume-button volume-down"></div>

        {/* Phone body */}
        <div className="phone-body">
          {/* Notch */}
          <div className="phone-notch">
            <div className="notch-speaker"></div>
            <div className="notch-camera"></div>
          </div>

          {/* Screen content */}
          <div className="phone-screen">
            {children}
          </div>

          {/* Home indicator (for modern iPhones) */}
          <div className="home-indicator"></div>
        </div>
      </div>
    </div>
  );
};
