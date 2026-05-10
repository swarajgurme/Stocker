/**
 * API Client Service
 * Centralized API communication with error handling
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000';

// Store and product constants
export const STORES = ['S001', 'S002', 'S003', 'S004', 'S005'];

export const PRODUCTS = [
  'Air Filter', 'Alternator', 'Battery', 'Brake Pad', 'Coolant',
  'Disc Rotor', 'Engine Oil', 'Fans', 'Fuse', 'LED',
  'Radiator', 'Rearview Mirror', 'Resistors', 'Sensor',
  'Sideview Mirror', 'Spark Plugs', 'Thermostat', 'Water Pump',
  'Windshield', 'Wires'
];

export const CATEGORIES = [
  'Accessories', 'Breaks', 'Cooling System', 'Electrical', 'Engine'
];

/**
 * Generic API request helper
 */
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  // Include auth token if available
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, config);
    const data = await response.json();

    // Standardized response handling
    if (data.status === 'success') {
      return { success: true, data: data.data };
    } else {
      // Error response from API
      const error = new Error(data.error || 'API request failed');
      error.code = data.code || 'API_ERROR';
      error.details = data.details;
      error.status = response.status;
      throw error;
    }
  } catch (error) {
    // Network or parse error
    if (!error.code) {
      error.code = 'NETWORK_ERROR';
      error.message = error.message || 'Network error occurred';
    }
    throw error;
  }
}

/**
 * Authentication APIs
 */
export const authAPI = {
  login: (email, password) =>
    apiRequest('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  register: (email, password, fullName, role = 'business_analyst') =>
    apiRequest('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name: fullName, role }),
    }),

  refresh: (refreshToken) =>
    apiRequest('/api/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),

  logout: () =>
    apiRequest('/api/auth/logout', { method: 'POST' }),

  getMe: () => apiRequest('/api/auth/me'),
};

/**
 * Forecast APIs
 */
export const forecastAPI = {
  generate: (params) =>
    apiRequest('/api/forecast/generate', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  get: (forecastId) => apiRequest(`/api/forecast/${forecastId}`),

  list: (filters = {}) =>
    apiRequest(`/api/forecast?${new URLSearchParams(filters)}`),

  delete: (forecastId) =>
    apiRequest(`/api/forecast/${forecastId}`, { method: 'DELETE' }),
};

/**
 * Inventory APIs
 */
export const inventoryAPI = {
  getLevels: (params = {}) =>
    apiRequest(`/api/inventory/levels?${new URLSearchParams(params)}`),

  updateLevel: (levelId, updates) =>
    apiRequest(`/api/inventory/levels/${levelId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    }),

  getReorderPoint: (storeId, productName) =>
    apiRequest(`/api/inventory/reorder-point/${storeId}/${productName}`),

  getAlerts: (params = {}) =>
    apiRequest(`/api/inventory/alerts?${new URLSearchParams(params)}`),

  resolveAlert: (alertId, notes = '') =>
    apiRequest(`/api/inventory/alerts/${alertId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ resolution_notes: notes }),
    }),

  bulkUpdate: (updates) =>
    apiRequest('/api/inventory/levels/bulk-update', {
      method: 'POST',
      body: JSON.stringify(updates),
    }),
};

/**
 * Analytics APIs
 */
export const analyticsAPI = {
  getClusters: (params = {}) =>
    apiRequest(`/api/analytics/clusters?${new URLSearchParams(params)}`),

  getDashboard: () => apiRequest('/api/analytics/dashboard/kpi'),

  getSalesByCategory: (period = 'all') =>
    apiRequest(`/api/analytics/sales-by-category?period=${period}`),

  compareStores: (metric = 'revenue', period = 'last_30_days') =>
    apiRequest(`/api/analytics/store-comparison?metric=${metric}&period=${period}`),
};

/**
 * Anomaly Detection APIs
 */
export const anomalyAPI = {
  detect: (params = {}) =>
    apiRequest('/api/anomalies/detect/sales', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  list: (params = {}) =>
    apiRequest(`/api/anomalies?${new URLSearchParams(params)}`),

  review: (anomalyId, isFalsePositive = false) =>
    apiRequest(`/api/anomalies/${anomalyId}/review`, {
      method: 'POST',
      body: JSON.stringify({ is_false_positive: isFalsePositive }),
    }),
};

/**
 * Recommendation APIs
 */
export const recommendationAPI = {
  list: (params = {}) =>
    apiRequest(`/api/recommendations?${new URLSearchParams(params)}`),

  generate: (params = {}) =>
    apiRequest('/api/recommendations/generate', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  act: (recId, notes = '') =>
    apiRequest(`/api/recommendations/${recId}/act`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    }),
};

/**
 * Report APIs
 */
export const reportAPI = {
  generate: (params) =>
    apiRequest('/api/reports/generate', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  listScheduled: () => apiRequest('/api/reports/scheduled'),

  schedule: (config) =>
    apiRequest('/api/reports/schedule', {
      method: 'POST',
      body: JSON.stringify(config),
    }),
};
