const API_BASE = import.meta.env.VITE_API_URL ?? "";

export const STORES = ["S001", "S002", "S003", "S004", "S005"];

export const CATEGORIES = [
  "Accessories",
  "Breaks",
  "Cooling System",
  "Electrical",
  "Engine",
];

export const PRODUCTS = [
  "Air Filter",
  "Alternator",
  "Battery",
  "Brake Pad",
  "Coolant",
  "Disc Rotor",
  "Engine Oil",
  "Fans",
  "Fuse",
  "LED",
  "Radiator",
  "Rearview Mirror",
  "Resistors",
  "Sensor",
  "Sideview Mirror",
  "Spark Plugs",
  "Thermostat",
  "Water Pump",
  "Windshield",
  "Wires",
];

type ApiEnvelope<T> =
  | { status: "success"; data: T }
  | { status: "error"; error?: string; code?: string };

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit & { skipJson?: boolean } = {},
): Promise<{ success: true; data: T } | never> {
  const { skipJson, ...fetchOpts } = options;
  const url = `${API_BASE}${endpoint}`;
  const token = localStorage.getItem("access_token");

  const response = await fetch(url, {
    ...fetchOpts,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(fetchOpts.headers ?? {}),
    },
  });

  if (skipJson) {
    if (!response.ok) {
      const err = new Error(`HTTP ${response.status}`) as Error & {
        code?: string;
        status?: number;
      };
      err.status = response.status;
      throw err;
    }
    return { success: true, data: undefined as T };
  }

  let body: ApiEnvelope<T> | null = null;
  try {
    body = (await response.json()) as ApiEnvelope<T>;
  } catch {
    const err = new Error("Invalid JSON response") as Error & { status?: number };
    err.status = response.status;
    throw err;
  }

  if (body.status === "success") {
    return { success: true, data: (body.data ?? {}) as T };
  }

  const err = new Error(
    typeof body.error === "string" ? body.error : "API request failed",
  ) as Error & { code?: string; status?: number; details?: unknown };
  err.code = body.code;
  err.status = response.status;
  throw err;
}

export const authAPI = {
  login: (email: string, password: string) =>
    apiRequest<Record<string, unknown>>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (
    email: string,
    password: string,
    fullName?: string,
    role = "business_analyst",
  ) =>
    apiRequest<Record<string, unknown>>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        full_name: fullName ?? "",
        role,
      }),
    }),
  refresh: (refreshToken: string) =>
    apiRequest<{ access_token: string; refresh_token?: string }>(
      "/api/auth/refresh",
      {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken }),
      },
    ),
  logout: () =>
    apiRequest<{ logged_out?: boolean }>("/api/auth/logout", {
      method: "POST",
    }),
  me: () => apiRequest<UserProfile>("/api/auth/me"),
};

export type UserProfile = {
  user_id: number;
  email: string;
  full_name: string | null;
  role: string;
};

export const forecastAPI = {
  generate: (params: Record<string, unknown>) =>
    apiRequest<ForecastGenerateResult>("/api/forecast/generate", {
      method: "POST",
      body: JSON.stringify(params),
    }),
  list: (q = "") =>
    apiRequest<{
      forecasts: Array<Record<string, unknown>>;
      total: number;
    }>(`/api/forecast${q ? `?${q}` : ""}`),
};

export type ForecastGenerateResult = {
  forecast_id: number;
  store_id: string;
  product_name: string;
  model_type: string;
  forecast: Array<{
    date: string;
    predicted: number;
    lower_bound: number;
    upper_bound: number;
  }>;
  metrics: { rmse: number | null; mae: number | null; mape: number | null };
  execution_time_seconds: number;
};

export const inventoryAPI = {
  list: (params: Record<string, string> = {}) => {
    const q = new URLSearchParams(params).toString();
    return apiRequest<{ inventory: InventoryRow[]; count: number }>(
      `/api/inventory${q ? `?${q}` : ""}`,
    );
  },
  alerts: (params: Record<string, string> = {}) => {
    const q = new URLSearchParams(params).toString();
    return apiRequest<{ alerts: AlertRow[]; count: number }>(
      `/api/inventory/alerts${q ? `?${q}` : ""}`,
    );
  },
};

export type InventoryRow = {
  id: number;
  store_id: string;
  product_name: string;
  category: string;
  current_stock: number;
  safety_stock: number;
  reorder_point: number;
  lead_time_days: number;
  status: string;
};

export type AlertRow = {
  id: number;
  store_id: string;
  product_name: string;
  alert_type: string;
  severity: string;
  message: string;
  created_at: string | null;
};

export const analyticsAPI = {
  dashboard: () =>
    apiRequest<DashboardPayload>("/api/analytics/dashboard"),
  clusters: () =>
    apiRequest<{
      analysis_date: string;
      assignments: ClusterRow[];
      statistics: Record<string, { count: number; total_sales: number; avg_sales: number }>;
    }>("/api/analytics/clusters"),
  salesByCategory: (period = "last_90_days") =>
    apiRequest<Array<{ category: string; total_sales: number; units: number }>>(
      `/api/analytics/sales-by-category?period=${period}`,
    ),
};

export type DashboardPayload = {
  revenue_trend: Array<{ month: string; revenue: number }>;
  forecast_accuracy: { avg_mape: number; interpretation: string };
  inventory_turnover: number;
  low_stock_count: number;
  anomalies_open: number;
  active_stores: number;
  demand_risk_score: number;
  top_stores: Array<{ store_id: string; revenue: number }>;
  category_performance: Array<{
    category: string;
    revenue: number;
    quantity: number;
  }>;
};

export type ClusterRow = {
  store_id: string;
  product_name: string | null;
  category: string;
  sales_ewma: number;
  cluster: number;
};

export const anomalyAPI = {
  list: (params: Record<string, string> = {}) => {
    const q = new URLSearchParams(params).toString();
    return apiRequest<{
      anomalies: AnomalyRow[];
      count?: number;
    }>(`/api/anomalies${q ? `?${q}` : ""}`);
  },
  detect: (body: Record<string, unknown>) =>
    apiRequest<{ anomalies_detected: number; anomalies: AnomalyRow[] }>(
      "/api/anomalies/detect/sales",
      { method: "POST", body: JSON.stringify(body) },
    ),
};

export type AnomalyRow = {
  id?: number;
  anomaly_type?: string;
  severity?: string;
  score?: number;
  description?: string;
  detection_date?: string;
  store_id?: string;
};

export const recommendationAPI = {
  list: () =>
    apiRequest<{ recommendations: RecommendationRow[]; count: number }>(
      "/api/recommendations",
    ),
  generate: (body: Record<string, unknown> = {}) =>
    apiRequest<{ generated: number; recommendations: unknown[] }>(
      "/api/recommendations/generate",
      { method: "POST", body: JSON.stringify(body) },
    ),
  act: (id: number, notes = "") =>
    apiRequest<unknown>(`/api/recommendations/${id}/act`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    }),
};

export type RecommendationRow = {
  id: number;
  store_id: string | null;
  product_name: string | null;
  type: string;
  priority: number;
  title: string;
  description: string;
  rationale: string | null;
  confidence_score: number;
  expected_impact: string | null;
  created_at: string | null;
};

export const reportAPI = {
  generate: (body: Record<string, unknown>) =>
    apiRequest<{ download_url: string; format: string }>(
      "/api/reports/generate",
      { method: "POST", body: JSON.stringify(body) },
    ),
};

export async function downloadAuthorizedFile(path: string): Promise<Blob> {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error(`Download failed (${res.status})`);
  return res.blob();
}
