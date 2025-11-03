import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { GeneratePage } from './pages/GeneratePage';
import { CallbackPage } from './pages/CallbackPage';
import { isAuthenticated, login, logout, getUserInfo } from './services/auth';
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
        <Routes>
          <Route path="/callback" element={<CallbackPage />} />
          <Route 
            path="/" 
            element={
              authenticated ? (
                <GeneratePage 
                  onLogout={logout}
                  userInfo={userInfo}
                />
              ) : (
                <LoginPage onLogin={login} />
              )
            } 
          />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </div>
    </Router>
  );
}

// Simple login page
const LoginPage = ({ onLogin }) => {
  return (
    <div style={styles.loginContainer}>
      <div style={styles.loginCard}>
        <h1 style={styles.title}>ProfilePhotoAI</h1>
        <p style={styles.subtitle}>AI로 완벽한 프로필 사진을 만들어보세요</p>
        
        <div style={styles.features}>
          <div style={styles.feature}>
            <span style={styles.featureIcon}>🎨</span>
            <p>다양한 스타일 선택</p>
          </div>
          <div style={styles.feature}>
            <span style={styles.featureIcon}>⚡</span>
            <p>빠른 생성 속도</p>
          </div>
          <div style={styles.feature}>
            <span style={styles.featureIcon}>🎯</span>
            <p>전문적인 품질</p>
          </div>
        </div>

        <button 
          onClick={onLogin}
          style={styles.loginButton}
        >
          로그인 / 회원가입
        </button>

        <p style={styles.note}>
          * Cognito Hosted UI로 안전하게 로그인됩니다
        </p>
      </div>
    </div>
  );
};

const styles = {
  loginContainer: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  },
  loginCard: {
    backgroundColor: 'white',
    padding: '60px 40px',
    borderRadius: '16px',
    boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
    textAlign: 'center',
    maxWidth: '500px',
    width: '90%',
  },
  title: {
    fontSize: '42px',
    fontWeight: 'bold',
    marginBottom: '10px',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  subtitle: {
    fontSize: '18px',
    color: '#666',
    marginBottom: '40px',
  },
  features: {
    display: 'flex',
    justifyContent: 'space-around',
    marginBottom: '40px',
    padding: '0 20px',
  },
  feature: {
    flex: 1,
  },
  featureIcon: {
    fontSize: '32px',
    display: 'block',
    marginBottom: '10px',
  },
  loginButton: {
    width: '100%',
    padding: '16px',
    fontSize: '18px',
    fontWeight: 'bold',
    color: 'white',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'transform 0.2s',
    marginBottom: '20px',
  },
  note: {
    fontSize: '14px',
    color: '#999',
    marginTop: '20px',
  },
};

export default App;
