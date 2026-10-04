import { mockAnalysisData } from '../data/mockAnalysis';

/**
 * TruthLens API Service
 */

// Normalized base URL without trailing slash
const defaultApiUrl = import.meta.env.DEV ? 'http://localhost:8000/api' : '/api';
const API_BASE = (import.meta.env.VITE_API_URL || defaultApiUrl).replace(/\/+$/, '');
const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === 'true';

export class ApiError extends Error {
  constructor(message, status = 500, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Submits a social media URL for analysis
 * @param {string} url
 * @param {boolean} [forceMock=false]
 * @returns {Promise<object>} UnifiedAnalysisResponse
 */
export async function analyzePost(url, forceMock = false) {
  const cleanUrl = url?.trim();
  if (!cleanUrl) {
    throw new ApiError('Please enter a valid social media URL.', 400);
  }

  // If mock mode is explicitly enabled or requested
  if (USE_MOCK || forceMock) {
    // Artificial small delay to give realistic UX
    await new Promise((resolve) => setTimeout(resolve, 1800));
    return JSON.parse(JSON.stringify(mockAnalysisData));
  }

  const endpoint = `${API_BASE}/v1/analyze`;

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url: cleanUrl }),
    });

    let json;
    try {
      json = await response.json();
    } catch {
      if (!response.ok) {
        throw new ApiError(
          `Server returned an error (${response.status}) with an unparseable response.`,
          response.status
        );
      }
      throw new ApiError('Received malformed response from the TruthLens verification server.', 500);
    }

    if (!response.ok) {
      const serverMessage = json?.message || json?.detail || json?.error;
      const platform = json?.platform;

      switch (response.status) {
        case 400:
          throw new ApiError(
            serverMessage || 'This URL is unsupported or invalid. Please check the link and try again.',
            400,
            json
          );
        case 404:
          throw new ApiError(
            serverMessage || 'The requested resource or post could not be found.',
            404,
            json
          );
        case 422:
          throw new ApiError(
            serverMessage || 'The URL format was rejected by the server validator.',
            422,
            json
          );
        case 429:
          throw new ApiError(
            serverMessage || 'TruthLens is receiving high traffic right now. Please wait a minute and try again.',
            429,
            json
          );
        case 501:
          throw new ApiError(
            serverMessage || `${platform ? platform.toUpperCase() : 'This platform'} is not yet supported for automated analysis.`,
            501,
            json
          );
        case 502:
          throw new ApiError(
            serverMessage || 'Could not retrieve post content from the social media provider. The post may be private, expired, or temporarily restricted.',
            502,
            json
          );
        case 500:
        default:
          throw new ApiError(
            serverMessage || 'An unexpected error occurred while analyzing the post. Please try again later.',
            response.status,
            json
          );
      }
    }

    if (!json || (!json.data && !json.analysis)) {
      throw new ApiError('Invalid response format received from TruthLens analysis API.', 500, json);
    }

    return json;
  } catch (err) {
    if (err instanceof ApiError) {
      throw err;
    }

    // Network failures / fetch rejections
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new ApiError(
        'Unable to connect to TruthLens analysis service. Please check your internet connection or verify the backend is running.',
        0
      );
    }

    throw new ApiError(err.message || 'An unexpected network error occurred.', 500);
  }
}

/**
 * Register a new user account
 * @param {object} payload - { name, email, password }
 * @returns {Promise<object>} AuthResponse { user, access_token }
 */
export async function signupApi({ name, email, password }) {
  const endpoint = `${API_BASE}/v1/auth/signup`;

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    });

    let json;
    try {
      json = await response.json();
    } catch {
      throw new ApiError('Failed to parse server response', response.status);
    }

    if (!response.ok) {
      const msg = json?.detail || json?.message || 'Failed to create account.';
      throw new ApiError(msg, response.status, json);
    }

    return json;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError('Unable to connect to authentication service.', 0);
  }
}

/**
 * Log in an existing user
 * @param {object} payload - { email, password }
 * @returns {Promise<object>} AuthResponse { user, access_token }
 */
export async function loginApi({ email, password }) {
  const endpoint = `${API_BASE}/v1/auth/login`;

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    let json;
    try {
      json = await response.json();
    } catch {
      throw new ApiError('Failed to parse server response', response.status);
    }

    if (!response.ok) {
      const msg = json?.detail || json?.message || 'Invalid email or password.';
      throw new ApiError(msg, response.status, json);
    }

    return json;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError('Unable to connect to authentication service.', 0);
  }
}

/**
 * Fetch profile of current user with JWT token
 * @param {string} token
 * @returns {Promise<object>} UserResponse
 */
export async function getMeApi(token) {
  const endpoint = `${API_BASE}/v1/auth/me`;

  try {
    const response = await fetch(endpoint, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new ApiError('Session expired or invalid', response.status);
    }

    return await response.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError('Failed to verify user session.', 0);
  }
}

/**
 * Log out user (notifies backend)
 */
export async function logoutApi() {
  try {
    await fetch(`${API_BASE}/v1/auth/logout`, { method: 'POST' });
  } catch {
    // Silent fail on network
  }
}

