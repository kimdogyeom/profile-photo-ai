import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { GeneratePage } from './pages/GeneratePage';
import { CallbackPage } from './pages/CallbackPage';
import AuthModal from './components/auth/AuthModal';
import { PhoneFrame } from './components/PhoneFrame';
import { Logo } from './components/Logo';
import { PaletteIcon, ZapIcon, TargetIcon, UploadIcon, GoogleIcon } from './components/Icons';
import { isAuthenticated, logout, getUserInfo } from './services/auth';
import './App.css';

function App() {
  const [authenticated, setAuthenticated] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check authentication status on mount
    const checkAuth = () => {
      const authed = isAuthenticated();
      setAuthenticated(authed);
      
      if (authed) {
        const info = getUserInfo();
        setUserInfo(info);
      }
      
      setLoading(false);
    };

    checkAuth();
  }, []);

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <Router>
      <div className="App">
        <ToastContainer
          position="top-center"
          autoClose={3000}
          hideProgressBar={false}
          newestOnTop
          closeOnClick
          rtl={false}
          pauseOnFocusLoss
          draggable
          pauseOnHover
          theme="dark"
          style={{ zIndex: 9999 }}
        />
        <Routes>
          <Route path="/callback" element={<CallbackPage />} />
          <Route 
            path="/generate" 
            element={
              authenticated ? (
                <GeneratePage 
                  onLogout={logout}
                  userInfo={userInfo}
                />
              ) : (
                <Navigate to="/" />
              )
            } 
          />
          <Route 
            path="/" 
            element={
              authenticated ? (
                <Navigate to="/generate" />
              ) : (
                <LandingPage />
              )
            } 
          />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </div>
    </Router>
  );
}

// Landing page with features
const LandingPage = () => {
  const [showAuthModal, setShowAuthModal] = useState(false);

  const handleAuthClick = () => {
    setShowAuthModal(true);
  };

  const handleAuthSuccess = () => {
    console.log('✅ Auth successful, redirecting to generate page');
    window.location.href = '/generate';
  };

  return (
    <>
      <AuthModal 
        isOpen={showAuthModal} 
        onClose={() => setShowAuthModal(false)}
        onSuccess={handleAuthSuccess}
      />
    <div style={styles.loginContainer}>
      {/* Background pattern */}
      <div style={styles.backgroundPattern}></div>

      {/* Semi-transparent overlay */}
      <div style={styles.overlay}></div>

      {/* Content */}
      <div style={styles.contentWrapper} className="login-page-content">
        {/* Left side - Text and CTA */}
        <div style={styles.leftSection} className="login-page-left">
          <Logo size="xlarge" variant="full" />
          <p style={styles.subtitle} className="login-page-subtitle">AI로 완벽한 프로필 사진을 만들어보세요</p>

          <div style={styles.features} className="login-page-features">
            <div style={styles.feature} className="login-page-feature">
              <div style={styles.featureIconWrapper}>
                <PaletteIcon size={32} color="#667eea" />
              </div>
              <div>
                <h3 style={styles.featureTitle} className="login-page-feature-title">다양한 스타일</h3>
                <p style={styles.featureText} className="login-page-feature-text">프로페셔널, 캐주얼 등 원하는 스타일 선택</p>
              </div>
            </div>
            <div style={styles.feature} className="login-page-feature">
              <div style={styles.featureIconWrapper}>
                <ZapIcon size={32} color="#667eea" />
              </div>
              <div>
                <h3 style={styles.featureTitle} className="login-page-feature-title">빠른 생성</h3>
                <p style={styles.featureText} className="login-page-feature-text">AI가 몇 분 안에 완성합니다</p>
              </div>
            </div>
            <div style={styles.feature} className="login-page-feature">
              <div style={styles.featureIconWrapper}>
                <TargetIcon size={32} color="#667eea" />
              </div>
              <div>
                <h3 style={styles.featureTitle} className="login-page-feature-title">전문 품질</h3>
                <p style={styles.featureText} className="login-page-feature-text">고해상도의 전문적인 결과물</p>
              </div>
            </div>
          </div>

          <div style={styles.buttonGroup} className="button-group">
            <button
              onClick={handleAuthClick}
              style={styles.primaryButton}
              className="login-page-button primary-btn"
              onMouseEnter={(e) => {
                e.target.style.transform = 'translateY(-2px)';
                e.target.style.boxShadow = '0 12px 32px rgba(102, 126, 234, 0.5)';
              }}
              onMouseLeave={(e) => {
                e.target.style.transform = 'translateY(0)';
                e.target.style.boxShadow = '0 8px 24px rgba(102, 126, 234, 0.4)';
              }}
            >
              로그인
            </button>

            <button
              onClick={handleAuthClick}
              style={styles.secondaryButton}
              className="login-page-button secondary-btn"
              onMouseEnter={(e) => {
                e.target.style.background = 'rgba(102, 126, 234, 0.15)';
                e.target.style.transform = 'translateY(-2px)';
              }}
              onMouseLeave={(e) => {
                e.target.style.background = 'rgba(102, 126, 234, 0.1)';
                e.target.style.transform = 'translateY(0)';
              }}
            >
              회원가입
            </button>
          </div>

          <p style={styles.note}>
            * 안전하게 로그인됩니다
          </p>
        </div>

        {/* Right side - Phone mockup */}
        <div style={styles.rightSection} className="login-page-right">
          <PhoneFrame>
            <div style={styles.phoneContent}>
              <div style={styles.mockHeader}>
                <div style={styles.logoBadge}>
                  <Logo size="small" variant="full" />
                </div>
              </div>
              <div style={styles.mockBody}>
                <div style={styles.mockUploadArea}>
                  <UploadIcon size={40} color="#999" />
                  <p style={styles.mockUploadText}>사진 업로드</p>
                </div>
                <div style={styles.mockStyles}>
                  <div style={styles.mockStyleCard}>Professional</div>
                  <div style={styles.mockStyleCard}>Casual</div>
                  <div style={styles.mockStyleCard}>Creative</div>
                </div>
                <div style={styles.mockButton}>생성하기</div>
              </div>
            </div>
          </PhoneFrame>
        </div>
      </div>
    </div>
    </>
  );
};

const styles = {
  loginContainer: {
    position: 'relative',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    overflow: 'hidden',
  },
  backgroundPattern: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: `
      radial-gradient(circle at 20% 50%, rgba(102, 126, 234, 0.15) 0%, transparent 50%),
      radial-gradient(circle at 80% 80%, rgba(118, 75, 162, 0.15) 0%, transparent 50%),
      radial-gradient(circle at 40% 20%, rgba(52, 152, 219, 0.1) 0%, transparent 50%),
      linear-gradient(135deg, #0f0f0f 0%, #1a1a1a 50%, #0a0a0a 100%)
    `,
    zIndex: 1,
  },
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0, 0, 0, 0.6)',
    backdropFilter: 'blur(2px)',
    zIndex: 2,
  },
  contentWrapper: {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    maxWidth: '1200px',
    width: '90%',
    gap: '60px',
    zIndex: 3,
    padding: '40px 0',
  },
  leftSection: {
    flex: 1,
    color: 'white',
    maxWidth: '600px',
  },
  rightSection: {
    flex: '0 0 auto',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  subtitle: {
    fontSize: '24px',
    color: '#e0e0e0',
    marginBottom: '60px',
    marginTop: '24px',
    lineHeight: '1.5',
  },
  features: {
    display: 'flex',
    flexDirection: 'column',
    gap: '30px',
    marginBottom: '50px',
  },
  feature: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '20px',
  },
  featureIconWrapper: {
    width: '56px',
    height: '56px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(102, 126, 234, 0.1)',
    borderRadius: '12px',
    flexShrink: 0,
    border: '1px solid rgba(102, 126, 234, 0.2)',
  },
  featureTitle: {
    fontSize: '20px',
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: '8px',
    marginTop: 0,
  },
  featureText: {
    fontSize: '16px',
    color: '#b0b0b0',
    margin: 0,
    lineHeight: '1.6',
  },
  buttonGroup: {
    display: 'flex',
    gap: '16px',
    marginBottom: '24px',
  },
  primaryButton: {
    flex: 1,
    padding: '16px 32px',
    fontSize: '18px',
    fontWeight: 'bold',
    color: 'white',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    border: 'none',
    borderRadius: '12px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    boxShadow: '0 8px 24px rgba(102, 126, 234, 0.4)',
  },
  secondaryButton: {
    flex: 1,
    padding: '16px 32px',
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#667eea',
    background: 'rgba(102, 126, 234, 0.1)',
    border: '2px solid #667eea',
    borderRadius: '12px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    backdropFilter: 'blur(10px)',
  },
  divider: {
    position: 'relative',
    textAlign: 'center',
    margin: '32px 0',
  },
  dividerText: {
    position: 'relative',
    display: 'inline-block',
    padding: '0 16px',
    color: '#808080',
    fontSize: '14px',
    zIndex: 1,
  },
  googleButton: {
    width: '100%',
    padding: '14px 24px',
    fontSize: '16px',
    fontWeight: '600',
    color: '#3c4043',
    background: 'white',
    border: '1px solid #dadce0',
    borderRadius: '12px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
    marginBottom: '24px',
  },
  note: {
    fontSize: '14px',
    color: '#808080',
    marginTop: '8px',
  },
  // Phone content mockup styles
  phoneContent: {
    width: '100%',
    height: '100%',
    background: 'linear-gradient(to bottom, #f8f9fa 0%, #ffffff 100%)',
    display: 'flex',
    flexDirection: 'column',
  },
  mockHeader: {
    padding: '48px 20px 20px',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
  },
  logoBadge: {
    background: 'rgba(255, 255, 255, 0.95)',
    backdropFilter: 'blur(10px)',
    padding: '12px 24px',
    borderRadius: '50px',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 4px 16px rgba(0, 0, 0, 0.15)',
    border: '1px solid rgba(255, 255, 255, 0.5)',
  },
  mockBody: {
    flex: 1,
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '15px',
  },
  mockUploadArea: {
    background: '#f0f0f0',
    borderRadius: '12px',
    padding: '30px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    border: '2px dashed #ccc',
  },
  mockUploadText: {
    fontSize: '14px',
    color: '#666',
    margin: 0,
  },
  mockStyles: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
  },
  mockStyleCard: {
    flex: '1 1 auto',
    background: 'white',
    border: '2px solid #667eea',
    borderRadius: '8px',
    padding: '12px',
    fontSize: '12px',
    textAlign: 'center',
    fontWeight: 'bold',
    color: '#667eea',
  },
  mockButton: {
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: 'white',
    padding: '14px',
    borderRadius: '8px',
    textAlign: 'center',
    fontWeight: 'bold',
    fontSize: '14px',
    marginTop: 'auto',
  },
};

export default App;
