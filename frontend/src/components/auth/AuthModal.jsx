import React, { useState } from 'react';
import './AuthModal.css';
import { 
  signIn, 
  signUp, 
  confirmSignUp, 
  resendConfirmationCode, 
  forgotPassword, 
  confirmPassword as resetPasswordWithCode 
} from '../../services/cognitoAuth';
import { getCognitoAuthUrl } from '../../config/aws-config';

const AuthModal = ({ isOpen, onClose, onSuccess }) => {
  const [view, setView] = useState('login'); // 'login' | 'signup' | 'verify' | 'forgot'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [resetCode, setResetCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  if (!isOpen) return null;

  const resetForm = () => {
    setEmail('');
    setPassword('');
    setConfirmPassword('');
    setDisplayName('');
    setVerificationCode('');
    setResetCode('');
    setNewPassword('');
    setError('');
    setSuccess('');
  };

  const handleClose = () => {
    resetForm();
    setView('login');
    onClose();
  };

  // 로그인
  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await signIn(email, password);
      console.log('✅ Login successful');
      if (onSuccess) onSuccess();
      handleClose();
    } catch (err) {
      console.error('❌ Login failed:', err);
      
      if (err.code === 'UserNotConfirmedException') {
        setError('이메일 인증이 필요합니다.');
        setView('verify');
      } else if (err.code === 'NotAuthorizedException') {
        setError('이메일 또는 비밀번호가 올바르지 않습니다.');
      } else if (err.code === 'UserNotFoundException') {
        setError('존재하지 않는 사용자입니다.');
      } else {
        setError(err.message || '로그인에 실패했습니다.');
      }
    } finally {
      setLoading(false);
    }
  };

  // 회원가입
  const handleSignup = async (e) => {
    e.preventDefault();
    setError('');

    if (password.length < 8) {
      setError('비밀번호는 최소 8자 이상이어야 합니다.');
      return;
    }
    if (!/[A-Z]/.test(password) || !/[a-z]/.test(password) || !/[0-9]/.test(password) || !/[^A-Za-z0-9]/.test(password)) {
      setError('비밀번호는 대소문자, 숫자, 특수문자를 포함해야 합니다.');
      return;
    }
    if (password !== confirmPassword) {
      setError('비밀번호가 일치하지 않습니다.');
      return;
    }

    setLoading(true);

    try {
      await signUp(email, password, displayName);
      console.log('✅ Signup successful');
      setSuccess('회원가입이 완료되었습니다! 이메일을 확인해주세요.');
      setView('verify');
    } catch (err) {
      console.error('❌ Signup failed:', err);
      
      if (err.code === 'UsernameExistsException') {
        setError('이미 등록된 이메일입니다.');
      } else if (err.code === 'InvalidPasswordException') {
        setError('비밀번호가 정책을 만족하지 않습니다.');
      } else {
        setError(err.message || '회원가입에 실패했습니다.');
      }
    } finally {
      setLoading(false);
    }
  };

  // 이메일 인증
  const handleVerify = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await confirmSignUp(email, verificationCode);
      console.log('✅ Email verified');
      setSuccess('이메일 인증이 완료되었습니다! 로그인해주세요.');
      setTimeout(() => {
        setView('login');
        setSuccess('');
      }, 2000);
    } catch (err) {
      console.error('❌ Verification failed:', err);
      
      if (err.code === 'CodeMismatchException') {
        setError('인증 코드가 올바르지 않습니다.');
      } else if (err.code === 'ExpiredCodeException') {
        setError('인증 코드가 만료되었습니다. 새 코드를 요청해주세요.');
      } else {
        setError(err.message || '인증에 실패했습니다.');
      }
    } finally {
      setLoading(false);
    }
  };

  // 인증 코드 재전송
  const handleResendCode = async () => {
    setError('');
    setLoading(true);

    try {
      await resendConfirmationCode(email);
      setSuccess('인증 코드가 재전송되었습니다.');
    } catch (err) {
      setError(err.message || '코드 재전송에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 비밀번호 재설정 코드 요청
  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await forgotPassword(email);
      setSuccess('비밀번호 재설정 코드가 이메일로 전송되었습니다.');
      setView('reset');
    } catch (err) {
      console.error('❌ Forgot password failed:', err);
      setError(err.message || '코드 전송에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 비밀번호 재설정
  const handleResetPassword = async (e) => {
    e.preventDefault();
    setError('');

    if (newPassword !== confirmPassword) {
      setError('비밀번호가 일치하지 않습니다.');
      return;
    }

    setLoading(true);

    try {
      await resetPasswordWithCode(email, resetCode, newPassword);
      setSuccess('비밀번호가 재설정되었습니다! 로그인해주세요.');
      setTimeout(() => {
        setView('login');
        setSuccess('');
      }, 2000);
    } catch (err) {
      console.error('❌ Reset password failed:', err);
      setError(err.message || '비밀번호 재설정에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // Google 로그인
  const handleGoogleLogin = () => {
    const googleAuthUrl = getCognitoAuthUrl('Google');
    console.log('🔐 Redirecting to Google OAuth:', googleAuthUrl);
    window.location.href = googleAuthUrl;
  };

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      handleClose();
    }
  };

  return (
    <div className="auth-modal-backdrop" onClick={handleBackdropClick}>
      <div className="auth-modal-content">
        <button className="auth-modal-close" onClick={handleClose}>×</button>

        {/* 로그인 뷰 */}
        {view === 'login' && (
          <>
            <h2 className="auth-modal-title">로그인</h2>
            
            {error && <div className="auth-modal-error">{error}</div>}
            {success && <div className="auth-modal-success">{success}</div>}

            <form onSubmit={handleLogin} className="auth-modal-form">
              <div className="form-group">
                <label>이메일</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  required
                  disabled={loading}
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label>비밀번호</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  disabled={loading}
                />
              </div>

              <button type="submit" className="auth-modal-btn-primary" disabled={loading}>
                {loading ? '로그인 중...' : '로그인'}
              </button>
            </form>

            <div className="auth-modal-divider">
              <span>또는</span>
            </div>

            <button onClick={handleGoogleLogin} className="auth-modal-btn-google" disabled={loading}>
              <svg className="google-icon" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Google로 계속하기
            </button>

            <div className="auth-modal-footer">
              <button className="link-button" onClick={() => { setError(''); setView('forgot'); }}>
                비밀번호를 잊으셨나요?
              </button>
              <div className="signup-prompt">
                계정이 없으신가요?{' '}
                <button className="link-button-primary" onClick={() => { resetForm(); setView('signup'); }}>
                  회원가입
                </button>
              </div>
            </div>
          </>
        )}

        {/* 회원가입 뷰 */}
        {view === 'signup' && (
          <>
            <h2 className="auth-modal-title">회원가입</h2>
            
            {error && <div className="auth-modal-error">{error}</div>}

            <form onSubmit={handleSignup} className="auth-modal-form">
              <div className="form-group">
                <label>이름</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="홍길동"
                  disabled={loading}
                />
              </div>

              <div className="form-group">
                <label>이메일 *</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  required
                  disabled={loading}
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label>비밀번호 *</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  disabled={loading}
                />
                <small className="form-hint">최소 8자, 대소문자, 숫자, 특수문자 포함</small>
              </div>

              <div className="form-group">
                <label>비밀번호 확인 *</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  disabled={loading}
                />
              </div>

              <button type="submit" className="auth-modal-btn-primary" disabled={loading}>
                {loading ? '가입 중...' : '회원가입'}
              </button>
            </form>

            <div className="auth-modal-divider">
              <span>또는</span>
            </div>

            <button onClick={handleGoogleLogin} className="auth-modal-btn-google" disabled={loading}>
              <svg className="google-icon" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Google로 계속하기
            </button>

            <div className="auth-modal-footer">
              <div className="signup-prompt">
                이미 계정이 있으신가요?{' '}
                <button className="link-button-primary" onClick={() => { resetForm(); setView('login'); }}>
                  로그인
                </button>
              </div>
            </div>
          </>
        )}

        {/* 이메일 인증 뷰 */}
        {view === 'verify' && (
          <>
            <div className="verification-icon">📧</div>
            <h2 className="auth-modal-title">이메일 인증</h2>
            <p className="auth-modal-description">
              <strong>{email}</strong>으로 발송된<br />
              인증 코드를 입력해주세요.
            </p>

            {error && <div className="auth-modal-error">{error}</div>}
            {success && <div className="auth-modal-success">{success}</div>}

            <form onSubmit={handleVerify} className="auth-modal-form">
              <div className="form-group">
                <label>인증 코드</label>
                <input
                  type="text"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value.replace(/\s/g, ''))}
                  placeholder="123456"
                  required
                  disabled={loading}
                  maxLength={6}
                  className="code-input"
                  autoFocus
                />
              </div>

              <button type="submit" className="auth-modal-btn-primary" disabled={loading}>
                {loading ? '확인 중...' : '인증 확인'}
              </button>
            </form>

            <div className="auth-modal-footer">
              <button className="link-button" onClick={handleResendCode} disabled={loading}>
                인증 코드 재전송
              </button>
              <button className="link-button" onClick={() => { resetForm(); setView('login'); }}>
                로그인으로 돌아가기
              </button>
            </div>
          </>
        )}

        {/* 비밀번호 찾기 뷰 */}
        {view === 'forgot' && (
          <>
            <h2 className="auth-modal-title">비밀번호 재설정</h2>
            <p className="auth-modal-description">
              가입하신 이메일 주소를 입력하시면<br />
              비밀번호 재설정 코드를 보내드립니다.
            </p>

            {error && <div className="auth-modal-error">{error}</div>}
            {success && <div className="auth-modal-success">{success}</div>}

            <form onSubmit={handleForgotPassword} className="auth-modal-form">
              <div className="form-group">
                <label>이메일</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  required
                  disabled={loading}
                  autoFocus
                />
              </div>

              <button type="submit" className="auth-modal-btn-primary" disabled={loading}>
                {loading ? '전송 중...' : '인증 코드 전송'}
              </button>
            </form>

            <div className="auth-modal-footer">
              <button className="link-button" onClick={() => { resetForm(); setView('login'); }}>
                로그인으로 돌아가기
              </button>
            </div>
          </>
        )}

        {/* 비밀번호 재설정 뷰 */}
        {view === 'reset' && (
          <>
            <h2 className="auth-modal-title">새 비밀번호 설정</h2>
            <p className="auth-modal-description">
              이메일로 받은 인증 코드와<br />
              새 비밀번호를 입력해주세요.
            </p>

            {error && <div className="auth-modal-error">{error}</div>}
            {success && <div className="auth-modal-success">{success}</div>}

            <form onSubmit={handleResetPassword} className="auth-modal-form">
              <div className="form-group">
                <label>인증 코드</label>
                <input
                  type="text"
                  value={resetCode}
                  onChange={(e) => setResetCode(e.target.value)}
                  placeholder="123456"
                  required
                  disabled={loading}
                  maxLength={6}
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label>새 비밀번호</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  disabled={loading}
                />
                <small className="form-hint">최소 8자, 대소문자, 숫자, 특수문자 포함</small>
              </div>

              <div className="form-group">
                <label>비밀번호 확인</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  disabled={loading}
                />
              </div>

              <button type="submit" className="auth-modal-btn-primary" disabled={loading}>
                {loading ? '재설정 중...' : '비밀번호 재설정'}
              </button>
            </form>

            <div className="auth-modal-footer">
              <button className="link-button" onClick={() => { resetForm(); setView('login'); }}>
                로그인으로 돌아가기
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default AuthModal;
