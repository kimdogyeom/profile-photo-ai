import React, { useState, useRef, useEffect } from 'react';
import { toast } from 'react-toastify';
import './ImageUploader.css';

// 상수 분리
const FILE_CONFIG = {
  ALLOWED_TYPES: ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'],
  ALLOWED_EXTENSIONS: 'JPG, PNG, WEBP',
  MAX_SIZE: 10 * 1024 * 1024, // 10MB
  DESKTOP_BREAKPOINT: 768
};

const WEBCAM_CONFIG = {
  DEFAULT_QUALITY: 0.92,
  VIDEO_CONSTRAINTS: {
    facingMode: 'user',
    width: { ideal: 1280 },
    height: { ideal: 720 }
  }
};

const WEBCAM_STATES = {
  IDLE: 'idle',
  LOADING: 'loading',
  ACTIVE: 'active',
  ERROR: 'error'
};

export const ImageUploader = ({ onFileSelect, selectedFile }) => {
  const [dragActive, setDragActive] = useState(false);
  const [preview, setPreview] = useState(null);
  const [isWebcamMode, setIsWebcamMode] = useState(false);
  const [webcamState, setWebcamState] = useState(WEBCAM_STATES.IDLE);
  const [isDesktop, setIsDesktop] = useState(false);
  const [devices, setDevices] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState(null);
  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  // 디바이스 타입 감지 (PC: 768px 이상)
  useEffect(() => {
    const checkDevice = () => {
      setIsDesktop(window.innerWidth >= FILE_CONFIG.DESKTOP_BREAKPOINT);
    };
    
    checkDevice();
    window.addEventListener('resize', checkDevice);
    return () => window.removeEventListener('resize', checkDevice);
  }, []);

  // 웹캠 디바이스 목록 가져오기
  useEffect(() => {
    const getDevices = async () => {
      try {
        const deviceList = await navigator.mediaDevices.enumerateDevices();
        const cameras = deviceList.filter(d => d.kind === 'videoinput');
        setDevices(cameras);
        if (cameras.length > 0 && !selectedDeviceId) {
          setSelectedDeviceId(cameras[0].deviceId);
        }
      } catch (error) {
        console.error('Failed to get devices:', error);
      }
    };

    if (isDesktop) {
      getDevices();
    }
  }, [isDesktop]);

  const validateFile = (file) => {
    if (!FILE_CONFIG.ALLOWED_TYPES.includes(file.type)) {
      throw new Error(`${FILE_CONFIG.ALLOWED_EXTENSIONS} 파일만 업로드 가능합니다.`);
    }

    if (file.size > FILE_CONFIG.MAX_SIZE) {
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
      toast.success('이미지가 선택되었습니다.', {
        position: "top-center",
        autoClose: 2000
      });
    } catch (error) {
      toast.error(error.message, {
        position: "top-center",
        autoClose: 3000
      });
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

  // 웹캠 시작 (개선된 상태 관리)
  const startWebcam = async () => {
    setWebcamState(WEBCAM_STATES.LOADING);
    setIsWebcamMode(true); // 먼저 웹캠 모드 활성화하여 video 엘리먼트 렌더링
    
    try {
      const constraints = { 
        video: { 
          deviceId: selectedDeviceId ? { exact: selectedDeviceId } : undefined,
          ...WEBCAM_CONFIG.VIDEO_CONSTRAINTS
        } 
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      
      streamRef.current = stream;
      
      // video 엘리먼트가 렌더링될 때까지 대기
      setTimeout(() => {
        if (videoRef.current && streamRef.current) {
          videoRef.current.srcObject = streamRef.current;
          
          videoRef.current.onloadedmetadata = () => {
            videoRef.current.play()
              .then(() => {
                setWebcamState(WEBCAM_STATES.ACTIVE);
                toast.success('웹캠이 시작되었습니다.', {
                  position: "top-center",
                  autoClose: 2000
                });
              })
              .catch((err) => {
                console.error('Video play error:', err);
                setWebcamState(WEBCAM_STATES.ERROR);
                toast.error('비디오 재생에 실패했습니다.', {
                  position: "top-center",
                  autoClose: 3000
                });
              });
          };
        } else {
          console.error('videoRef is still null after timeout');
          setWebcamState(WEBCAM_STATES.ERROR);
          toast.error('비디오 엘리먼트를 찾을 수 없습니다.', {
            position: "top-center",
            autoClose: 3000
          });
        }
      }, 100);
      
    } catch (error) {
      console.error('Webcam access error:', error);
      setWebcamState(WEBCAM_STATES.ERROR);
      setIsWebcamMode(false);
      
      let errorMessage = '웹캠에 접근할 수 없습니다.';
      if (error.name === 'NotAllowedError') {
        errorMessage = '웹캠 권한이 거부되었습니다. 브라우저 설정을 확인해주세요.';
      } else if (error.name === 'NotFoundError') {
        errorMessage = '웹캠을 찾을 수 없습니다.';
      } else if (error.name === 'NotReadableError') {
        errorMessage = '웹캠이 다른 앱에서 사용 중입니다.';
      }
      
      toast.error(errorMessage, {
        position: "top-center",
        autoClose: 4000
      });
    }
  };

  // 웹캠 종료
  const stopWebcam = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    setIsWebcamMode(false);
    setWebcamState(WEBCAM_STATES.IDLE);
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
      toast.warning('웹캠이 아직 준비 중입니다. 잠시 후 다시 시도해주세요.', {
        position: "top-center",
        autoClose: 3000
      });
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
        toast.error('사진 캡처에 실패했습니다. 다시 시도해주세요.', {
          position: "top-center",
          autoClose: 3000
        });
      }
    }, 'image/jpeg', WEBCAM_CONFIG.DEFAULT_QUALITY);
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
            <>
              {devices.length > 1 && (
                <select 
                  value={selectedDeviceId || ''} 
                  onChange={(e) => setSelectedDeviceId(e.target.value)}
                  className="device-selector"
                >
                  {devices.map((device, index) => (
                    <option key={device.deviceId} value={device.deviceId}>
                      {device.label || `카메라 ${index + 1}`}
                    </option>
                  ))}
                </select>
              )}
              <button 
                onClick={startWebcam} 
                className="webcam-button"
                type="button"
                disabled={webcamState === WEBCAM_STATES.LOADING}
              >
                {webcamState === WEBCAM_STATES.LOADING ? '⏳ 웹캠 시작 중...' : '🎥 웹캠으로 촬영'}
              </button>
            </>
          )}
        </>
      ) : isWebcamMode ? (
        <div className="webcam-container">
          {/* 로딩 오버레이 */}
          {webcamState === WEBCAM_STATES.LOADING && (
            <div className="webcam-loading-overlay">
              <div className="loading-spinner"></div>
              <p>웹캠 준비 중...</p>
            </div>
          )}
          
          {/* video 엘리먼트는 항상 렌더링 (로딩 중엔 숨김) */}
          <video 
            ref={videoRef} 
            autoPlay 
            playsInline 
            muted
            className="webcam-video"
            style={{ 
              display: webcamState === WEBCAM_STATES.ACTIVE ? 'block' : 'none' 
            }}
          />
          <canvas ref={canvasRef} style={{ display: 'none' }} />
          
          {webcamState === WEBCAM_STATES.ACTIVE && (
            <div className="webcam-controls">
              <button onClick={capturePhoto} className="capture-button">
                📸 사진 촬영
              </button>
              <button onClick={stopWebcam} className="cancel-button">
                취소
              </button>
            </div>
          )}
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
