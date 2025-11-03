/**
 * Cognito Direct Authentication Service (Custom UI)
 * - Email/Password signup, login, verification
 * - Uses amazon-cognito-identity-js
 */

import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserAttribute,
} from 'amazon-cognito-identity-js';
import config from '../config/aws-config';

// Initialize Cognito User Pool
const poolData = {
  UserPoolId: config.cognito.userPoolId,
  ClientId: config.cognito.clientId,
};

const userPool = new CognitoUserPool(poolData);

// Local storage keys (same as existing auth.js)
const TOKEN_KEY = 'idToken';
const ACCESS_TOKEN_KEY = 'accessToken';
const REFRESH_TOKEN_KEY = 'refreshToken';
const USER_INFO_KEY = 'userInfo';

/**
 * Sign up a new user with email and password
 * @param {string} email - User email
 * @param {string} password - User password
 * @param {string} displayName - User display name
 * @returns {Promise<Object>} - { user, userConfirmed, userSub }
 */
export const signUp = (email, password, displayName) => {
  return new Promise((resolve, reject) => {
    const attributeList = [
      new CognitoUserAttribute({ Name: 'email', Value: email }),
    ];

    if (displayName) {
      attributeList.push(
        new CognitoUserAttribute({ Name: 'name', Value: displayName })
      );
    }

    userPool.signUp(
      email,
      password,
      attributeList,
      null,
      (err, result) => {
        if (err) {
          console.error('❌ Signup error:', err);
          reject(err);
          return;
        }

        console.log('✅ Signup success:', {
          username: result.user.getUsername(),
          userConfirmed: result.userConfirmed,
          userSub: result.userSub,
        });

        resolve({
          user: result.user,
          userConfirmed: result.userConfirmed,
          userSub: result.userSub,
        });
      }
    );
  });
};

/**
 * Confirm user email with verification code
 * @param {string} username - User email
 * @param {string} code - Verification code from email
 * @returns {Promise<string>} - Confirmation result
 */
export const confirmSignUp = (username, code) => {
  return new Promise((resolve, reject) => {
    const cognitoUser = new CognitoUser({
      Username: username,
      Pool: userPool,
    });

    cognitoUser.confirmRegistration(code, true, (err, result) => {
      if (err) {
        console.error('❌ Confirmation error:', err);
        reject(err);
        return;
      }

      console.log('✅ Email confirmed:', result);
      resolve(result);
    });
  });
};

/**
 * Resend verification code to email
 * @param {string} username - User email
 * @returns {Promise<string>} - Result message
 */
export const resendConfirmationCode = (username) => {
  return new Promise((resolve, reject) => {
    const cognitoUser = new CognitoUser({
      Username: username,
      Pool: userPool,
    });

    cognitoUser.resendConfirmationCode((err, result) => {
      if (err) {
        console.error('❌ Resend code error:', err);
        reject(err);
        return;
      }

      console.log('✅ Code resent:', result);
      resolve(result);
    });
  });
};

/**
 * Sign in user with email and password
 * @param {string} username - User email
 * @param {string} password - User password
 * @returns {Promise<Object>} - { idToken, accessToken, refreshToken, userInfo }
 */
export const signIn = (username, password) => {
  return new Promise((resolve, reject) => {
    const authenticationDetails = new AuthenticationDetails({
      Username: username,
      Password: password,
    });

    const cognitoUser = new CognitoUser({
      Username: username,
      Pool: userPool,
    });

    cognitoUser.authenticateUser(authenticationDetails, {
      onSuccess: (result) => {
        const idToken = result.getIdToken().getJwtToken();
        const accessToken = result.getAccessToken().getJwtToken();
        const refreshToken = result.getRefreshToken().getToken();

        // Parse user info from ID token
        const userInfo = parseJwt(idToken);

        // Store tokens in localStorage
        localStorage.setItem(TOKEN_KEY, idToken);
        localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
        localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
        localStorage.setItem(USER_INFO_KEY, JSON.stringify(userInfo));

        console.log('✅ Login success:', {
          username: userInfo.email || userInfo['cognito:username'],
          sub: userInfo.sub,
        });

        resolve({
          idToken,
          accessToken,
          refreshToken,
          userInfo,
        });
      },

      onFailure: (err) => {
        console.error('❌ Login error:', err);
        reject(err);
      },

      newPasswordRequired: (userAttributes, requiredAttributes) => {
        console.warn('⚠️ New password required');
        reject({
          code: 'NewPasswordRequired',
          message: 'New password required',
          userAttributes,
          requiredAttributes,
        });
      },
    });
  });
};

/**
 * Sign out current user
 */
export const signOut = () => {
  const cognitoUser = userPool.getCurrentUser();

  if (cognitoUser) {
    cognitoUser.signOut();
    console.log('✅ User signed out');
  }

  // Clear local storage
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_INFO_KEY);
};

/**
 * Get current authenticated user
 * @returns {Promise<Object>} - { idToken, accessToken, userInfo }
 */
export const getCurrentUser = () => {
  return new Promise((resolve, reject) => {
    const cognitoUser = userPool.getCurrentUser();

    if (!cognitoUser) {
      reject(new Error('No user logged in'));
      return;
    }

    cognitoUser.getSession((err, session) => {
      if (err) {
        console.error('❌ Session error:', err);
        reject(err);
        return;
      }

      if (!session.isValid()) {
        reject(new Error('Session is invalid'));
        return;
      }

      const idToken = session.getIdToken().getJwtToken();
      const accessToken = session.getAccessToken().getJwtToken();
      const userInfo = parseJwt(idToken);

      resolve({
        idToken,
        accessToken,
        userInfo,
      });
    });
  });
};

/**
 * Refresh tokens using refresh token
 * @returns {Promise<Object>} - { idToken, accessToken }
 */
export const refreshSession = () => {
  return new Promise((resolve, reject) => {
    const cognitoUser = userPool.getCurrentUser();

    if (!cognitoUser) {
      reject(new Error('No user logged in'));
      return;
    }

    cognitoUser.getSession((err, session) => {
      if (err) {
        reject(err);
        return;
      }

      // Session automatically refreshes if refresh token is valid
      const idToken = session.getIdToken().getJwtToken();
      const accessToken = session.getAccessToken().getJwtToken();

      // Update localStorage
      localStorage.setItem(TOKEN_KEY, idToken);
      localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);

      console.log('✅ Token refreshed');

      resolve({
        idToken,
        accessToken,
      });
    });
  });
};

/**
 * Forgot password - send reset code to email
 * @param {string} username - User email
 * @returns {Promise<Object>} - CodeDeliveryDetails
 */
export const forgotPassword = (username) => {
  return new Promise((resolve, reject) => {
    const cognitoUser = new CognitoUser({
      Username: username,
      Pool: userPool,
    });

    cognitoUser.forgotPassword({
      onSuccess: (data) => {
        console.log('✅ Reset code sent:', data);
        resolve(data);
      },
      onFailure: (err) => {
        console.error('❌ Forgot password error:', err);
        reject(err);
      },
    });
  });
};

/**
 * Confirm password reset with code
 * @param {string} username - User email
 * @param {string} code - Verification code
 * @param {string} newPassword - New password
 * @returns {Promise<string>} - Result message
 */
export const confirmPassword = (username, code, newPassword) => {
  return new Promise((resolve, reject) => {
    const cognitoUser = new CognitoUser({
      Username: username,
      Pool: userPool,
    });

    cognitoUser.confirmPassword(code, newPassword, {
      onSuccess: () => {
        console.log('✅ Password reset successful');
        resolve('Password reset successful');
      },
      onFailure: (err) => {
        console.error('❌ Password reset error:', err);
        reject(err);
      },
    });
  });
};

/**
 * Check if user is authenticated
 * @returns {boolean}
 */
export const isAuthenticated = () => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) return false;

  try {
    const payload = parseJwt(token);
    const expirationTime = payload.exp * 1000;
    return Date.now() < expirationTime;
  } catch (error) {
    return false;
  }
};

/**
 * Get ID token from localStorage
 * @returns {string|null}
 */
export const getIdToken = () => {
  return localStorage.getItem(TOKEN_KEY);
};

/**
 * Get access token from localStorage
 * @returns {string|null}
 */
export const getAccessToken = () => {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
};

/**
 * Parse JWT token
 * @param {string} token - JWT token
 * @returns {Object} - Decoded payload
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
    return {};
  }
};
