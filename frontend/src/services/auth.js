const CLIENT_ID = process.env.REACT_APP_COGNITO_CLIENT_ID || '';
const COGNITO_DOMAIN = process.env.REACT_APP_COGNITO_DOMAIN || '';
const REDIRECT_URI = process.env.REACT_APP_REDIRECT_URI || '';
const LOGOUT_URI = process.env.REACT_APP_LOGOUT_URI || '';

const TOKEN_KEY = 'idToken';
const ACCESS_TOKEN_KEY = 'accessToken';
const REFRESH_TOKEN_KEY = 'refreshToken';
const USER_INFO_KEY = 'userInfo';
const PKCE_VERIFIER_KEY = 'auth.pkce.verifier';
const PKCE_STATE_KEY = 'auth.pkce.state';
const PKCE_NONCE_KEY = 'auth.pkce.nonce';

const AUTH_SCOPES = ['openid', 'email', 'profile'];
const DEFAULT_CALLBACK_PATH = '/callback';

const getWindow = () => (typeof window !== 'undefined' ? window : null);

const ensureStorage = () => {
  const currentWindow = getWindow();

  if (!currentWindow) {
    throw new Error('Browser environment is required.');
  }

  return currentWindow;
};

const ensureHostedUiConfig = () => {
  if (!CLIENT_ID || !COGNITO_DOMAIN) {
    throw new Error('Cognito Hosted UI configuration is missing.');
  }
};

const getRedirectUri = () => {
  if (REDIRECT_URI) {
    return REDIRECT_URI;
  }

  const currentWindow = ensureStorage();
  return `${currentWindow.location.origin}${DEFAULT_CALLBACK_PATH}`;
};

const getLogoutUri = () => {
  if (LOGOUT_URI) {
    return LOGOUT_URI;
  }

  const currentWindow = ensureStorage();
  return currentWindow.location.origin;
};

const getCallbackPath = () => {
  try {
    return new URL(getRedirectUri()).pathname;
  } catch (error) {
    return DEFAULT_CALLBACK_PATH;
  }
};

const parseJwt = (token) => {
  const base64Url = token.split('.')[1];

  if (!base64Url) {
    throw new Error('Invalid JWT token.');
  }

  const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
  const jsonPayload = decodeURIComponent(
    atob(base64)
      .split('')
      .map((char) => `%${`00${char.charCodeAt(0).toString(16)}`.slice(-2)}`)
      .join('')
  );

  return JSON.parse(jsonPayload);
};

const safeParseJwt = (token) => {
  try {
    return parseJwt(token);
  } catch (error) {
    return null;
  }
};

const base64UrlEncode = (buffer) => {
  const bytes = new Uint8Array(buffer);
  let binary = '';

  for (let index = 0; index < bytes.byteLength; index += 1) {
    binary += String.fromCharCode(bytes[index]);
  }

  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
};

const encodeText = (value) => {
  if (typeof TextEncoder !== 'undefined') {
    return new TextEncoder().encode(value);
  }

  const bytes = new Uint8Array(value.length);

  for (let index = 0; index < value.length; index += 1) {
    bytes[index] = value.charCodeAt(index);
  }

  return bytes;
};

const generateRandomString = (length) => {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
  const currentWindow = ensureStorage();
  const randomValues = new Uint8Array(length);

  currentWindow.crypto.getRandomValues(randomValues);

  return Array.from(randomValues, (value) => alphabet[value % alphabet.length]).join('');
};

const createPkcePair = async () => {
  const currentWindow = ensureStorage();
  const verifier = generateRandomString(96);
  const digest = await currentWindow.crypto.subtle.digest(
    'SHA-256',
    encodeText(verifier)
  );

  return {
    codeVerifier: verifier,
    codeChallenge: base64UrlEncode(digest),
  };
};

const clearAuthTransaction = () => {
  const currentWindow = getWindow();

  if (!currentWindow) {
    return;
  }

  currentWindow.sessionStorage.removeItem(PKCE_VERIFIER_KEY);
  currentWindow.sessionStorage.removeItem(PKCE_STATE_KEY);
  currentWindow.sessionStorage.removeItem(PKCE_NONCE_KEY);
};

const storeAuthTransaction = ({ codeVerifier, state, nonce }) => {
  const currentWindow = ensureStorage();
  currentWindow.sessionStorage.setItem(PKCE_VERIFIER_KEY, codeVerifier);
  currentWindow.sessionStorage.setItem(PKCE_STATE_KEY, state);
  currentWindow.sessionStorage.setItem(PKCE_NONCE_KEY, nonce);
};

const getStoredAuthTransaction = () => {
  const currentWindow = getWindow();

  if (!currentWindow) {
    return { codeVerifier: null, state: null, nonce: null };
  }

  return {
    codeVerifier: currentWindow.sessionStorage.getItem(PKCE_VERIFIER_KEY),
    state: currentWindow.sessionStorage.getItem(PKCE_STATE_KEY),
    nonce: currentWindow.sessionStorage.getItem(PKCE_NONCE_KEY),
  };
};

const redirectTo = (url) => {
  const currentWindow = ensureStorage();
  currentWindow.location.assign(url);
  return url;
};

const buildHostedUiUrl = (path, extraParams = {}) => {
  const url = new URL(path, `https://${COGNITO_DOMAIN}`);
  url.searchParams.set('client_id', CLIENT_ID);
  url.searchParams.set('response_type', 'code');
  url.searchParams.set('redirect_uri', getRedirectUri());
  url.searchParams.set('scope', AUTH_SCOPES.join(' '));

  Object.entries(extraParams).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, value);
    }
  });

  return url.toString();
};

const buildLogoutUrl = () => {
  const url = new URL('/logout', `https://${COGNITO_DOMAIN}`);
  url.searchParams.set('client_id', CLIENT_ID);
  url.searchParams.set('logout_uri', getLogoutUri());
  return url.toString();
};

const postTokenRequest = async (body) => {
  const response = await fetch(`https://${COGNITO_DOMAIN}/oauth2/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams(body).toString(),
  });

  if (!response.ok) {
    let message = 'Failed to exchange authorization code.';

    try {
      const errorPayload = await response.json();
      message = errorPayload.error_description || errorPayload.error || message;
    } catch (error) {
      // Ignore response parsing errors and keep the generic message.
    }

    throw new Error(message);
  }

  return response.json();
};

const getTokenStorage = (currentWindow) => currentWindow.sessionStorage;

const storeSession = ({ idToken, accessToken, refreshToken }) => {
  const currentWindow = ensureStorage();
  const storage = getTokenStorage(currentWindow);
  storage.setItem(TOKEN_KEY, idToken);
  storage.setItem(ACCESS_TOKEN_KEY, accessToken);

  if (refreshToken) {
    storage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }

  const userInfo = safeParseJwt(idToken);
  if (userInfo) {
    storage.setItem(USER_INFO_KEY, JSON.stringify(userInfo));
  } else {
    storage.removeItem(USER_INFO_KEY);
  }
};

const startHostedUiFlow = async (path, extraParams = {}) => {
  ensureHostedUiConfig();

  const { codeVerifier, codeChallenge } = await createPkcePair();
  const state = generateRandomString(32);
  const nonce = generateRandomString(32);

  storeAuthTransaction({ codeVerifier, state, nonce });

  const url = buildHostedUiUrl(path, {
    ...extraParams,
    state,
    nonce,
    code_challenge: codeChallenge,
    code_challenge_method: 'S256',
  });

  redirectTo(url);
  return { url };
};

const exchangeAuthorizationCode = async (code) => {
  const { codeVerifier, state, nonce } = getStoredAuthTransaction();
  const currentWindow = ensureStorage();
  const callbackParams = new URLSearchParams(currentWindow.location.search);
  const returnedState = callbackParams.get('state');
  const returnedNonce = callbackParams.get('nonce');

  if (!codeVerifier) {
    throw new Error('Missing PKCE verifier.');
  }

  if (state && returnedState && state !== returnedState) {
    throw new Error('Invalid auth state.');
  }

  const tokenResponse = await postTokenRequest({
    client_id: CLIENT_ID,
    grant_type: 'authorization_code',
    code,
    redirect_uri: getRedirectUri(),
    code_verifier: codeVerifier,
  });

  const idTokenPayload = safeParseJwt(tokenResponse.id_token);

  if (nonce && idTokenPayload?.nonce && idTokenPayload.nonce !== nonce) {
    throw new Error('Invalid auth nonce.');
  }

  if (returnedNonce && idTokenPayload?.nonce && idTokenPayload.nonce !== returnedNonce) {
    throw new Error('Invalid auth nonce.');
  }

  return {
    idToken: tokenResponse.id_token,
    accessToken: tokenResponse.access_token,
    refreshToken: tokenResponse.refresh_token || null,
  };
};

export const isAuthCallbackUrl = () => {
  const currentWindow = getWindow();

  if (!currentWindow) {
    return false;
  }

  return currentWindow.location.pathname === getCallbackPath();
};

export const handleAuthCallback = async () => {
  const currentWindow = getWindow();

  if (!currentWindow || !isAuthCallbackUrl()) {
    return { handled: false };
  }

  const searchParams = new URLSearchParams(currentWindow.location.search);
  const error = searchParams.get('error');

  if (error) {
    clearAuthTransaction();
    clearTokens();

    return {
      handled: true,
      error,
      errorDescription: searchParams.get('error_description') || '',
    };
  }

  const code = searchParams.get('code');

  if (!code) {
    return { handled: false };
  }

  try {
    const sessionTokens = await exchangeAuthorizationCode(code);
    storeSession(sessionTokens);
    clearAuthTransaction();

    return {
      handled: true,
      ...sessionTokens,
      userInfo: safeParseJwt(sessionTokens.idToken),
    };
  } catch (error) {
    clearAuthTransaction();
    throw error;
  }
};

export const signIn = (email) => startHostedUiFlow('/login', { login_hint: email });

export const signUp = (email) => startHostedUiFlow('/signup', { login_hint: email });

export const confirmSignUp = (email) => startHostedUiFlow('/confirm', { login_hint: email });

export const resendConfirmationCode = (email) => startHostedUiFlow('/resendcode', { login_hint: email });

export const forgotPassword = (email) => startHostedUiFlow('/forgotPassword', { login_hint: email });

export const confirmPassword = (email) => startHostedUiFlow('/confirmforgotPassword', { login_hint: email });

export const logout = ({ redirect = true } = {}) => {
  clearAuthTransaction();
  clearTokens();

  if (!redirect) {
    return;
  }

  if (!CLIENT_ID || !COGNITO_DOMAIN) {
    const currentWindow = getWindow();
    if (currentWindow) {
      currentWindow.location.assign(getLogoutUri());
    }
    return;
  }

  redirectTo(buildLogoutUrl());
};

export const getIdToken = () => {
  const currentWindow = getWindow();
  return currentWindow ? currentWindow.sessionStorage.getItem(TOKEN_KEY) : null;
};

export const getAccessToken = () => {
  const currentWindow = getWindow();
  return currentWindow ? currentWindow.sessionStorage.getItem(ACCESS_TOKEN_KEY) : null;
};

export const getRefreshToken = () => {
  const currentWindow = getWindow();
  return currentWindow ? currentWindow.sessionStorage.getItem(REFRESH_TOKEN_KEY) : null;
};

export const getUserInfo = () => {
  const currentWindow = getWindow();

  if (!currentWindow) {
    return null;
  }

  const value = currentWindow.sessionStorage.getItem(USER_INFO_KEY);

  if (!value) {
    return null;
  }

  try {
    return JSON.parse(value);
  } catch (error) {
    clearTokens();
    return null;
  }
};

export const clearTokens = () => {
  const currentWindow = getWindow();

  if (!currentWindow) {
    return;
  }

  currentWindow.sessionStorage.removeItem(TOKEN_KEY);
  currentWindow.sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  currentWindow.sessionStorage.removeItem(REFRESH_TOKEN_KEY);
  currentWindow.sessionStorage.removeItem(USER_INFO_KEY);
};

export const isAuthenticated = () => {
  const token = getIdToken();

  if (!token) {
    return false;
  }

  try {
    const payload = parseJwt(token);
    return payload.exp > Date.now() / 1000;
  } catch (error) {
    clearTokens();
    return false;
  }
};

export const refreshTokens = async () => {
  ensureHostedUiConfig();

  const refreshToken = getRefreshToken();

  if (!refreshToken) {
    throw new Error('No refresh token available');
  }

  try {
    const tokenResponse = await postTokenRequest({
      client_id: CLIENT_ID,
      grant_type: 'refresh_token',
      refresh_token: refreshToken,
    });

    const idToken = tokenResponse.id_token;
    const accessToken = tokenResponse.access_token;
    const nextRefreshToken = tokenResponse.refresh_token || refreshToken;

    storeSession({
      idToken,
      accessToken,
      refreshToken: nextRefreshToken,
    });

    return {
      idToken,
      accessToken,
      refreshToken: nextRefreshToken,
    };
  } catch (error) {
    clearTokens();
    throw error;
  }
};
