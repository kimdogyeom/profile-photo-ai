/**
 * Cognito OAuth2 Authentication Service
 */

const COGNITO_DOMAIN = process.env.REACT_APP_COGNITO_DOMAIN;
const CLIENT_ID = process.env.REACT_APP_COGNITO_CLIENT_ID;
const REDIRECT_URI = process.env.REACT_APP_REDIRECT_URI || window.location.origin + '/callback';
const LOGOUT_URI = process.env.REACT_APP_LOGOUT_URI || window.location.origin;

// Local storage keys
const TOKEN_KEY = 'idToken';
const ACCESS_TOKEN_KEY = 'accessToken';
const REFRESH_TOKEN_KEY = 'refreshToken';
const USER_INFO_KEY = 'userInfo';

/**
 * Redirect to Cognito Hosted UI for login
 */
export const login = () => {
  console.log('🔐 Login attempt:', {
    COGNITO_DOMAIN,
    CLIENT_ID,
    REDIRECT_URI,
  });
  
  const loginUrl = `${COGNITO_DOMAIN}/login?client_id=${CLIENT_ID}&response_type=code&scope=email+openid+profile&redirect_uri=${encodeURIComponent(REDIRECT_URI)}`;
  console.log('🔗 Login URL:', loginUrl);
  
  window.location.href = loginUrl;
};

/**
 * Redirect to Cognito Hosted UI for signup
 */
export const signup = () => {
  console.log('📝 Signup attempt:', {
    COGNITO_DOMAIN,
    CLIENT_ID,
    REDIRECT_URI,
  });
  
  const signupUrl = `${COGNITO_DOMAIN}/signup?client_id=${CLIENT_ID}&response_type=code&scope=email+openid+profile&redirect_uri=${encodeURIComponent(REDIRECT_URI)}`;
  console.log('🔗 Signup URL:', signupUrl);
  
  window.location.href = signupUrl;
};

/**
 * Logout user and redirect to Cognito logout
 */
export const logout = () => {
  clearTokens();
  const logoutUrl = `${COGNITO_DOMAIN}/logout?client_id=${CLIENT_ID}&logout_uri=${encodeURIComponent(LOGOUT_URI)}`;
  window.location.href = logoutUrl;
};

/**
 * Handle OAuth2 callback with authorization code
 * Exchange code for tokens
 */
export const handleCallback = async (code) => {
  try {
    // Clean domain (remove https:// if present)
    const cleanDomain = COGNITO_DOMAIN.replace(/^https?:\/\//, '');
    const tokenEndpoint = `https://${cleanDomain}/oauth2/token`;
    
    console.log('🔐 Token exchange attempt:', {
      tokenEndpoint,
      client_id: CLIENT_ID,
      redirect_uri: REDIRECT_URI,
      code: code.substring(0, 10) + '...'
    });
    
    const params = new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: CLIENT_ID,
      code: code,
      redirect_uri: REDIRECT_URI
    });

    const response = await fetch(tokenEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: params.toString()
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ Token exchange failed:', {
        status: response.status,
        statusText: response.statusText,
        body: errorText
      });
      
      let errorMessage = `토큰 교환 실패 (${response.status})`;
      try {
        const errorData = JSON.parse(errorText);
        if (errorData.error) {
          errorMessage = `${errorData.error}: ${errorData.error_description || ''}`;
        }
      } catch (e) {
        errorMessage += `: ${errorText}`;
      }
      
      throw new Error(errorMessage);
    }

    const tokens = await response.json();
    console.log('✅ Token exchange successful');
    
    // Store tokens
    localStorage.setItem(TOKEN_KEY, tokens.id_token);
    localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
    if (tokens.refresh_token) {
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
    }

    // Parse and store user info from id_token
    const userInfo = parseJwt(tokens.id_token);
    localStorage.setItem(USER_INFO_KEY, JSON.stringify(userInfo));

    return tokens;
  } catch (error) {
    console.error('❌ Failed to exchange code for tokens:', error);
    throw error;
  }
};

/**
 * Get current ID token
 */
export const getIdToken = () => {
  return localStorage.getItem(TOKEN_KEY);
};

/**
 * Get current access token
 */
export const getAccessToken = () => {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
};

/**
 * Get refresh token
 */
export const getRefreshToken = () => {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
};

/**
 * Get stored user info
 */
export const getUserInfo = () => {
  const userInfoStr = localStorage.getItem(USER_INFO_KEY);
  return userInfoStr ? JSON.parse(userInfoStr) : null;
};

/**
 * Check if user is authenticated
 */
export const isAuthenticated = () => {
  const token = getIdToken();
  if (!token) return false;

  // Check if token is expired
  try {
    const payload = parseJwt(token);
    const now = Date.now() / 1000;
    return payload.exp > now;
  } catch (error) {
    return false;
  }
};

/**
 * Refresh tokens using refresh token
 */
export const refreshTokens = async () => {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }

  try {
    const tokenEndpoint = `${COGNITO_DOMAIN}/oauth2/token`;
    
    const params = new URLSearchParams({
      grant_type: 'refresh_token',
      client_id: CLIENT_ID,
      refresh_token: refreshToken
    });

    const response = await fetch(tokenEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: params.toString()
    });

    if (!response.ok) {
      throw new Error(`Token refresh failed: ${response.status}`);
    }

    const tokens = await response.json();
    
    // Update tokens
    localStorage.setItem(TOKEN_KEY, tokens.id_token);
    localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);

    // Update user info
    const userInfo = parseJwt(tokens.id_token);
    localStorage.setItem(USER_INFO_KEY, JSON.stringify(userInfo));

    return tokens;
  } catch (error) {
    console.error('Failed to refresh tokens:', error);
    clearTokens();
    throw error;
  }
};

/**
 * Clear all stored tokens and user info
 */
export const clearTokens = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_INFO_KEY);
};

/**
 * Parse JWT token to get payload
 */
const parseJwt = (token) => {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (error) {
    console.error('Failed to parse JWT:', error);
    return null;
  }
};
