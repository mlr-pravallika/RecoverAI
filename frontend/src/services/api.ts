const API_BASE_URL = 'http://localhost:8000';

export interface Customer {
  id: string;
  name: string;
  email: string;
  phone?: string;
}

export interface PaymentAttempt {
  id: string;
  attempt_number: number;
  payment_method?: string;
  failure_code?: string;
  failure_reason?: string;
  status: string;
  created_at: string;
}

export interface RecoveryAction {
  id: number;
  recovery_case_id: number;
  action_type: string;
  status: string;
  details?: string;
  created_at: string;
  updated_at: string;
}

export interface RecoveryCase {
  id: number;
  transaction_id: string;
  status: string;
  recovery_probability: number;
  expected_recovery: number;
  recommended_action?: string;
  explanation?: string;
  retry_count: number;
  max_retries: number;
  created_at: string;
  updated_at: string;
  actions: RecoveryAction[];
}

export interface Transaction {
  id: string;
  customer_id: string;
  order_id?: string;
  amount: number;
  currency: string;
  status: string;
  payment_method?: string;
  failure_code?: string;
  failure_type?: string;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
  customer?: Customer;
  attempts: PaymentAttempt[];
  recovery_cases: RecoveryCase[];
}

export interface DashboardSummary {
  revenue_at_risk: number;
  expected_recovery: number;
  recovered_revenue: number;
  recovery_rate: number;
  active_recoveries: number;
  manual_reviews: number;
  blocked_actions: number;
  total_analyzed: number;
}

export interface WhatIfRequest {
  max_retries: number;
  min_confidence: number;
  recovery_window_hours: number;
  max_automated_amount: number;
}

export interface WhatIfPresetResult {
  preset_name: string;
  max_retries: number;
  min_confidence: number;
  max_automated_amount: number;
  recovery_rate: number;
  recovered_revenue: number;
  manual_review_rate: number;
  blocked_actions_count: number;
}

export interface WhatIfResponse {
  current: WhatIfPresetResult;
  presets: WhatIfPresetResult[];
  explanation: string;
}

export interface SimulationResponse {
  run_id: string;
  transactions_analyzed: number;
  revenue_at_risk: number;
  recoverable_transactions: number;
  actions_executed: number;
  recovered_revenue: number;
  recovery_rate: number;
  manual_escalations: number;
  unsafe_actions_prevented: number;
  strategy_distribution: Record<string, number>;
  failure_distribution: Record<string, number>;
}

export interface AuditLog {
  id: number;
  transaction_id?: string;
  recovery_case_id?: number;
  timestamp: string;
  actor: string;
  action: string;
  previous_state?: string;
  new_state?: string;
  reason?: string;
  metadata_json?: string;
}

export interface Merchant {
  id: string;
  business_name: string;
  owner_name: string;
  email: string;
  mode: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface RazorpayStatus {
  connected: boolean;
  mode: string;
  key_id_masked?: string;
  error?: string;
}

// Token helper methods
function getHeaders(): HeadersInit {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export const api = {
  setToken(token: string) {
    localStorage.setItem('token', token);
  },

  getToken(): string | null {
    return localStorage.getItem('token');
  },

  logout() {
    localStorage.removeItem('token');
  },

  async signup(payload: Record<string, string>): Promise<{ access_token: string; merchant: Merchant }> {
    const res = await fetch(`${API_BASE_URL}/api/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to create merchant account' }));
      throw new Error(err.detail || 'Failed to create merchant account');
    }
    return res.json();
  },

  async login(payload: Record<string, string>): Promise<{ access_token: string; merchant: Merchant }> {
    const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Invalid credentials' }));
      throw new Error(err.detail || 'Invalid credentials');
    }
    return res.json();
  },

  async getMerchantProfile(): Promise<Merchant> {
    const res = await fetch(`${API_BASE_URL}/api/merchant/profile`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch merchant profile');
    return res.json();
  },

  async updateMerchantMode(mode: string): Promise<{ success: boolean; mode: string }> {
    const res = await fetch(`${API_BASE_URL}/api/merchant/mode`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ mode }),
    });
    if (!res.ok) throw new Error('Failed to switch mode');
    return res.json();
  },

  async getRazorpayStatus(): Promise<RazorpayStatus> {
    const res = await fetch(`${API_BASE_URL}/api/integrations/razorpay/status`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch Razorpay connection status');
    return res.json();
  },

  async getGeminiStatus(): Promise<{ connected: boolean; active_model: string; error?: string; sdk: string; last_verified_at?: string }> {
    const res = await fetch(`${API_BASE_URL}/api/ai/gemini/status`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch Gemini connection status');
    return res.json();
  },

  async getGeminiModels(): Promise<{ configured: boolean; active_model: string; models: Array<{ name: string; display_name: string; description: string; verified: boolean; supports_recoverai: boolean }> }> {
    const res = await fetch(`${API_BASE_URL}/api/ai/models`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch Gemini models list');
    return res.json();
  },

  async verifyGeminiModel(modelName: string): Promise<{ model_name: string; verified: boolean; error?: string }> {
    const res = await fetch(`${API_BASE_URL}/api/ai/models/verify`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ model_name: modelName }),
    });
    if (!res.ok) throw new Error('Failed to verify model compatibility');
    return res.json();
  },

  async selectGeminiModel(modelName: string): Promise<{ success: boolean; active_model: string }> {
    const res = await fetch(`${API_BASE_URL}/api/ai/models/select`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ model_name: modelName }),
    });
    if (!res.ok) throw new Error('Failed to select model');
    return res.json();
  },

  async syncRazorpay(): Promise<{ success: boolean; fetched: number; created: number; updated: number; duplicates: number }> {
    const res = await fetch(`${API_BASE_URL}/api/integrations/razorpay/sync`, {
      method: 'POST',
      headers: getHeaders(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Synchronization failed' }));
      throw new Error(err.detail || 'Synchronization failed');
    }
    return res.json();
  },

  async getDashboardSummary(): Promise<DashboardSummary> {
    const res = await fetch(`${API_BASE_URL}/api/dashboard/summary`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch dashboard summary');
    return res.json();
  },

  async getTransactions(filters: {
    status?: string;
    failure_type?: string;
    recommended_action?: string;
    search?: string;
  } = {}): Promise<Transaction[]> {
    const params = new URLSearchParams();
    if (filters.status) params.append('status', filters.status);
    if (filters.failure_type) params.append('failure_type', filters.failure_type);
    if (filters.recommended_action) params.append('recommended_action', filters.recommended_action);
    if (filters.search) params.append('search', filters.search);
    params.append('limit', '100');

    const res = await fetch(`${API_BASE_URL}/api/transactions?${params.toString()}`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch transactions');
    return res.json();
  },

  async getTransaction(id: string): Promise<Transaction> {
    const res = await fetch(`${API_BASE_URL}/api/transactions/${id}`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch transaction details');
    return res.json();
  },

  async runSimulation(numTransactions: number, preset: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/recovery/run`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ num_transactions: numTransactions, policy_preset: preset }),
    });
    if (!res.ok) throw new Error('Failed to execute simulation run');
    return res.json();
  },

  async runWhatIf(config: WhatIfRequest): Promise<WhatIfResponse> {
    const res = await fetch(`${API_BASE_URL}/api/recovery/what-if`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error('Failed to run What-If evaluation');
    return res.json();
  },

  async stopRecoveryCase(caseId: number, reason: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/recovery/${caseId}/stop`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ reason }),
    });
    if (!res.ok) throw new Error('Failed to abort recovery case');
    return res.json();
  },

  async approveRecoveryCase(caseId: number): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/recovery/${caseId}/approve`, {
      method: 'POST',
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to approve recovery action');
    return res.json();
  },

  async rejectRecoveryCase(caseId: number, reason: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/recovery/${caseId}/reject`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ reason }),
    });
    if (!res.ok) throw new Error('Failed to reject recovery action');
    return res.json();
  },

  async getAuditLogs(): Promise<AuditLog[]> {
    const res = await fetch(`${API_BASE_URL}/api/audit/logs`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch audit logs');
    return res.json();
  },

  async triggerDemoFailure(scenario: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/recovery/simulate-failure`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ scenario }),
    });
    if (!res.ok) throw new Error('Failed to trigger demo failure');
    return res.json();
  },
  
  async getPolicyConfig(): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/policy/config`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch policy configuration');
    return res.json();
  },

  async updatePolicyConfig(config: WhatIfRequest): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/policy/config`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error('Failed to update policy configuration');
    return res.json();
  }
};
