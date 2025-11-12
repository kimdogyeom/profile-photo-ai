import React, { useState, useRef, useEffect } from 'react';
import './ImageUploader.css';

export const ImageUploader = ({ onFileSelect, selectedFile }) => {
  const [dragActive, setDragActive] = useState(false);
  const [preview, setPreview] = useState(null);
  const [isWebcamMode, setIsWebcamMode] = useState(false);
  const [isDesktop, setIsDesktop] = useState(false);
  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  // 디바이스 타입 감지 (PC: 768px 이상)
  useEffect(() => {
    const checkDevice = () => {
      setIsDesktop(window.innerWidth >= 768);
    };
    
    checkDevice();
    window.addEventListener('resize', checkDevice);
    return () => window.removeEventListener('resize', checkDevice);
  }, []);

  const validateFile = (file) => {
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    const maxSize = 10 * 1024 * 1024; // 10MB

    if (!allowedTypes.includes(file.type)) {
      throw new Error('JPG, PNG, WEBP 파일만 업로드 가능합니다.');
    }

    if (file.size > maxSize) {
      throw new Error('파일 크기는 10MB 이하여야 합니다.');
    }

    return true;
  };

  const handleFile = (file) => {
    try {
      validateFile(file);
      
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreview(e.target.result);
      };
      reader.readAsDataURL(file);
      
      onFileSelect(file);
    } catch (error) {
      alert(error.message);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleRemove = () => {
    setPreview(null);
    onFileSelect(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // 웹캠 시작
  const startWebcam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          facingMode: 'user',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        } 
      });
      
      streamRef.current = stream;
      setIsWebcamMode(true);
      
      // 다음 렌더링 사이클을 기다림
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          
          videoRef.current.onloadedmetadata = () => {
            videoRef.current.play().catch(err => {
              console.error('Video play error:', err);
              alert('비디오 재생에 실패했습니다.');
            });
          };
        }
      }, 100);
      
    } catch (error) {
      console.error('Webcam access error:', error);
      alert('웹캠에 접근할 수 없습니다. 브라우저 권한을 확인해주세요.');
      setIsWebcamMode(false);
    }
  };

  // 웹캠 종료
  const stopWebcam = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    setIsWebcamMode(false);
  };

  // 사진 캡처
  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) {
      console.error('Video or canvas ref is null');
      return;
    }

    const video = videoRef.current;
    const canvas = canvasRef.current;
    
    // 비디오가 준비되지 않았으면 대기
    if (video.videoWidth === 0 || video.videoHeight === 0) {
      alert('웹캠이 아직 준비 중입니다. 잠시 후 다시 시도해주세요.');
      return;
    }

    const context = canvas.getContext('2d');
    
    // 캔버스 크기를 비디오 크기에 맞춤
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    // 비디오 프레임을 캔버스에 그리기
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Blob으로 변환하여 File 객체 생성
    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], `webcam-${Date.now()}.jpg`, { type: 'image/jpeg' });
        handleFile(file);
        stopWebcam();
      } else {
        alert('사진 캡처에 실패했습니다. 다시 시도해주세요.');
      }
    }, 'image/jpeg', 0.95);
  };

  // 컴포넌트 언마운트 시 웹캠 정리
  useEffect(() => {
    return () => {
      stopWebcam();
    };
  }, []);

  return (
    <div className="image-uploader">
      <h3>이미지 업로드</h3>
      
      {!preview && !isWebcamMode ? (
        <>
          <div
            className={`upload-area ${dragActive ? 'drag-active' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={handleClick}
          >
            <div className="upload-icon">📷</div>
            <div className="upload-text">
              <p>클릭하거나 파일을 드래그하여 업로드</p>
              <p className="upload-hint">JPG, PNG, WEBP (최대 10MB)</p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/jpg,image/png,image/webp"
              onChange={handleChange}
              style={{ display: 'none' }}
            />
          </div>
          
          {/* PC에서만 웹캠 버튼 표시 */}
          {isDesktop && (
            <button 
              onClick={startWebcam} 
              className="webcam-button"
              type="button"
            >
              🎥 웹캠으로 촬영
            </button>
          )}
        </>
      ) : isWebcamMode ? (
        <div className="webcam-container">
          <video 
            ref={videoRef} 
            autoPlay 
            playsInline 
            muted
            className="webcam-video"
          />
          <canvas ref={canvasRef} style={{ display: 'none' }} />
          <div className="webcam-controls">
            <button onClick={capturePhoto} className="capture-button">
              📸 사진 촬영
            </button>
            <button onClick={stopWebcam} className="cancel-button">
              취소
            </button>
          </div>
        </div>
      ) : (
        <div className="preview-container">
          <img src={preview} alt="Preview" className="preview-image" />
          <div className="preview-info">
            <p className="file-name">{selectedFile?.name}</p>
            <p className="file-size">
              {(selectedFile?.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
          <button onClick={handleRemove} className="remove-button">
            다른 이미지 선택
          </button>
        </div>
      )}
    </div>
  );
};
