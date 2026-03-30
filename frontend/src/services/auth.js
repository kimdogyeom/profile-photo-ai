import {
  AuthenticationDetails,
  CognitoUser,
  CognitoUserAttribute,
  CognitoUserPool,
  CognitoRefreshToken,
} from 'amazon-cognito-identity-js';

const USER_POOL_ID = process.env.REACT_APP_COGNITO_USER_POOL_ID || '';
const CLIENT_ID = process.env.REACT_APP_COGNITO_CLIENT_ID || '';

const TOKEN_KEY = 'idToken';
const ACCESS_TOKEN_KEY = 'accessToken';
const REFRESH_TOKEN_KEY = 'refreshToken';
const USER_INFO_KEY = 'userInfo';

const userPool = new CognitoUserPool({
  UserPoolId: USER_POOL_ID,
  ClientId: CLIENT_ID,
});

const ensureConfig = () => {
  if (!USER_POOL_ID || !CLIENT_ID) {
    throw new Error('Cognito configuration is missing.');
  }
};

const parseJwt = (token) => {
  const base64Url = token.split('.')[1];
  const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
  const jsonPayload = decodeURIComponent(
    atob(base64)
      .split('')
      .map((char) => `%${`00${char.charCodeAt(0).toString(16)}`.slice(-2)}`)
      .join('')
  );
  return JSON.parse(jsonPayload);
};

const storeSession = ({ idToken, accessToken, refreshToken }) => {
  localStorage.setItem(TOKEN_KEY, idToken);
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  if (refreshToken) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }
  localStorage.setItem(USER_INFO_KEY, JSON.stringify(parseJwt(idToken)));
};

export const signUp = (email, password, displayName) =>
  new Promise((resolve, reject) => {
    ensureConfig();
    const attributes = [new CognitoUserAttribute({ Name: 'email', Value: email })];

    if (displayName) {
      attributes.push(new CognitoUserAttribute({ Name: 'name', Value: displayName }));
    }

    userPool.signUp(email, password, attributes, null, (error, result) => {
      if (error) {
        reject(error);
        return;
      }

      resolve({
        user: result.user,
        userConfirmed: result.userConfirmed,
        userSub: result.userSub,
      });
    });
  });

export const confirmSignUp = (email, code) =>
  new Promise((resolve, reject) => {
    ensureConfig();
    const cognitoUser = new CognitoUser({ Username: email, Pool: userPool });
    cognitoUser.confirmRegistration(code, true, (error, result) => {
      if (error) {
        reject(error);
        return;
      }
      resolve(result);
    });
  });

export const resendConfirmationCode = (email) =>
  new Promise((resolve, reject) => {
    ensureConfig();
    const cognitoUser = new CognitoUser({ Username: email, Pool: userPool });
    cognitoUser.resendConfirmationCode((error, result) => {
      if (error) {
        reject(error);
        return;
      }
      resolve(result);
    });
  });

export const signIn = (email, password) =>
  new Promise((resolve, reject) => {
    ensureConfig();
    const authenticationDetails = new AuthenticationDetails({ Username: email, Password: password });
    const cognitoUser = new CognitoUser({ Username: email, Pool: userPool });

    cognitoUser.authenticateUser(authenticationDetails, {
      onSuccess: (session) => {
        const idToken = session.getIdToken().getJwtToken();
        const accessToken = session.getAccessToken().getJwtToken();
        const refreshToken = session.getRefreshToken().getToken();

        storeSession({ idToken, accessToken, refreshToken });
        resolve({ idToken, accessToken, refreshToken, userInfo: parseJwt(idToken) });
      },
      onFailure: reject,
      newPasswordRequired: (userAttributes, requiredAttributes) => {
        reject({
          code: 'NewPasswordRequired',
          message: 'New password required',
          userAttributes,
          requiredAttributes,
        });
      },
    });
  });

export const forgotPassword = (email) =>
  new Promise((resolve, reject) => {
    ensureConfig();
    const cognitoUser = new CognitoUser({ Username: email, Pool: userPool });
    cognitoUser.forgotPassword({
      onSuccess: resolve,
      onFailure: reject,
      inputVerificationCode: () => resolve({ challenge: 'CODE_SENT' }),
    });
  });

export const confirmPassword = (email, code, newPassword) =>
  new Promise((resolve, reject) => {
    ensureConfig();
    const cognitoUser = new CognitoUser({ Username: email, Pool: userPool });
    cognitoUser.confirmPassword(code, newPassword, {
      onSuccess: resolve,
      onFailure: reject,
    });
  });

export const logout = () => {
  const cognitoUser = userPool.getCurrentUser();
  if (cognitoUser) {
    cognitoUser.signOut();
  }
  clearTokens();
};

export const getIdToken = () => localStorage.getItem(TOKEN_KEY);
export const getAccessToken = () => localStorage.getItem(ACCESS_TOKEN_KEY);
export const getRefreshToken = () => localStorage.getItem(REFRESH_TOKEN_KEY);

export const getUserInfo = () => {
  const value = localStorage.getItem(USER_INFO_KEY);
  return value ? JSON.parse(value) : null;
};

export const clearTokens = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_INFO_KEY);
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

export const refreshTokens = () =>
  new Promise((resolve, reject) => {
    ensureConfig();
    const cognitoUser = userPool.getCurrentUser();
    const refreshToken = getRefreshToken();

    if (!cognitoUser || !refreshToken) {
      reject(new Error('No refresh token available'));
      return;
    }

    cognitoUser.refreshSession(new CognitoRefreshToken({ RefreshToken: refreshToken }), (error, session) => {
      if (error) {
        clearTokens();
        reject(error);
        return;
      }

      const idToken = session.getIdToken().getJwtToken();
      const accessToken = session.getAccessToken().getJwtToken();
      const nextRefreshToken = session.getRefreshToken().getToken() || refreshToken;
      storeSession({ idToken, accessToken, refreshToken: nextRefreshToken });
      resolve({ idToken, accessToken, refreshToken: nextRefreshToken });
    });
  });
