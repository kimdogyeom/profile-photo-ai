import React, { useState } from 'react';
import { getStylesList, getStylePrompt } from '../config/prompts';
import './StyleSelector.css';

export const StyleSelector = ({ onStyleChange, selectedStyle }) => {
  const [customPrompt, setCustomPrompt] = useState('');
  const styles = getStylesList();

  const handleStyleSelect = (styleId) => {
    const prompt = getStylePrompt(styleId, customPrompt);
    onStyleChange({ styleId, prompt });
  };

  const handleCustomPromptChange = (text) => {
    setCustomPrompt(text);
    if (selectedStyle === 'custom') {
      const prompt = getStylePrompt('custom', text);
      onStyleChange({ styleId: 'custom', prompt });
    }
  };

  return (
    <div className="style-selector">
      <h3>스타일 선택</h3>
      
      <div className="style-grid">
        {styles.map((style) => (
          <div
            key={style.id}
            className={`style-card ${selectedStyle === style.id ? 'selected' : ''}`}
            onClick={() => handleStyleSelect(style.id)}
          >
            <div className="style-icon">{style.icon}</div>
            <div className="style-name">{style.name}</div>
            <div className="style-description">{style.description}</div>
          </div>
        ))}
      </div>

      {selectedStyle === 'custom' && (
        <div className="custom-prompt-input">
          <label htmlFor="custom-prompt">커스텀 프롬프트</label>
          <textarea
            id="custom-prompt"
            value={customPrompt}
            onChange={(e) => handleCustomPromptChange(e.target.value)}
            placeholder="원하는 프로필 사진 스타일을 자세히 설명해주세요..."
            maxLength={2000}
            rows={5}
          />
          <div className="character-count">
            {customPrompt.length} / 2000
          </div>
        </div>
      )}
    </div>
  );
};
