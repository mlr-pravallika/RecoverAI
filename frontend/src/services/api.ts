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

export const api = {
  async getDashboardSummary(): Promise<DashboardSummary> {
    const res = await fetch(`${API_BASE_URL}/api/dashboard/summary`);
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

    const res = await fetch(`${API_BASE_URL}/api/transactions?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch transactions');
    return res.json();
  },

  async getTransaction(id: string): Promise<Transaction> {
    const res = await fetch(`${API_BASE_URL}/api/transactions/${id}`);
    if (!res.ok) throw new Error('Failed to fetch transaction details');
    return res.json();
  },

  async runSimulation(numTransactions: number, preset: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/recovery/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ num_transactions: numTransactions, policy_preset: preset }),
    });
    if (!res.ok) throw new Error('Failed to execute simulation run');
    return res.json();
  },

  async runWhatIf(config: WhatIfRequest): Promise<WhatIfResponse> {
    const res = await fetch(`${API_BASE_URL}/api/recovery/what-if`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error('Failed to run What-If evaluation');
    return res.json();
  },

  async stopRecoveryCase(caseId: number, reason: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/recovery/${caseId}/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason }),
    });
    if (!res.ok) throw new Error('Failed to abort recovery case');
    return res.json();
  },

  async getAuditLogs(): Promise<AuditLog[]> {
    const res = await fetch(`${API_BASE_URL}/api/audit/logs`);
    if (!res.ok) throw new Error('Failed to fetch audit logs');
    return res.json();
  },

  async triggerDemoFailure(scenario: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/recovery/simulate-failure`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario }),
    });
    if (!res.ok) throw new Error('Failed to trigger demo failure');
    return res.json();
  },
  
  async getPolicyConfig(): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/policy/config`);
    if (!res.ok) throw new Error('Failed to fetch policy configuration');
    return res.json();
  },

  async updatePolicyConfig(config: WhatIfRequest): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/policy/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error('Failed to update policy configuration');
    return res.json();
  }
};
