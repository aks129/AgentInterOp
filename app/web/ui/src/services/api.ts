// API service for healthcare interoperability backend
export interface ApiResponse<T = any> {
  ok?: boolean;
  success?: boolean;
  error?: string;
  message?: string;
  data?: T;
}

export interface Protocol {
  protocol: 'a2a' | 'mcp';
}

export interface Scenario {
  name: string;
  label: string;
  requirements?: string;
  examples?: any[];
}

export interface ScenarioList {
  scenarios: Record<string, { label: string }>;
  active: string;
}

export interface FhirConfig {
  base: string;
  token?: string;
}

export interface PatientBundle {
  resourceType: 'Bundle';
  entry: Array<{
    resource: {
      resourceType: string;
      id?: string;
      [key: string]: any;
    };
  }>;
}

export interface TraceEvent {
  timestamp: string;
  actor: string;
  action: string;
  detail: any;
}

export interface TraceResponse {
  ok: boolean;
  context_id: string;
  events: TraceEvent[];
  count: number;
}

class ApiService {
  private baseUrl = '';

  async request<T = any>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }
      
      return response.text() as T;
    } catch (error) {
      console.error('API Request failed:', error);
      throw error;
    }
  }

  // Protocol Management
  async getCurrentProtocol(): Promise<Protocol> {
    return this.request<Protocol>('/api/current_protocol');
  }

  async switchProtocol(protocol: 'a2a' | 'mcp'): Promise<ApiResponse> {
    return this.request<ApiResponse>('/api/protocol', {
      method: 'POST',
      body: JSON.stringify({ protocol }),
    });
  }

  // Scenario Management
  async getScenarios(): Promise<ScenarioList> {
    return this.request<ScenarioList>('/api/scenarios');
  }

  async getActiveScenario(): Promise<Scenario> {
    return this.request<Scenario>('/api/scenarios/active');
  }

  async activateScenario(name: string): Promise<ApiResponse> {
    return this.request<ApiResponse>('/api/scenarios/activate', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  }

  async evaluateScenario(scenarioName: string, applicantPayload: any, patientBundle: any = {}): Promise<ApiResponse> {
    return this.request<ApiResponse>(`/api/scenarios/${scenarioName}/evaluate`, {
      method: 'POST',
      body: JSON.stringify({ applicant_payload: applicantPayload, patient_bundle: patientBundle }),
    });
  }

  async updateScenarioOptions(options: any): Promise<ApiResponse> {
    return this.request<ApiResponse>('/api/scenarios/options', {
      method: 'POST',
      body: JSON.stringify(options),
    });
  }

  // FHIR Integration
  async configureFhir(config: FhirConfig): Promise<ApiResponse> {
    return this.request<ApiResponse>('/api/fhir/config', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  async getFhirCapabilities(): Promise<any> {
    return this.request('/api/fhir/capabilities');
  }

  async searchPatients(params: { name?: string; identifier?: string }): Promise<PatientBundle> {
    const searchParams = new URLSearchParams();
    if (params.name) searchParams.append('name', params.name);
    if (params.identifier) searchParams.append('identifier', params.identifier);
    
    return this.request<PatientBundle>(`/api/fhir/patients?${searchParams.toString()}`);
  }

  async getPatientEverything(patientId: string): Promise<PatientBundle> {
    return this.request<PatientBundle>(`/api/fhir/patient/${patientId}/everything`);
  }

  async ingestPatientData(bundle: PatientBundle, patientId?: string): Promise<ApiResponse> {
    return this.request<ApiResponse>('/api/ingest', {
      method: 'POST',
      body: JSON.stringify({ bundle, patientId }),
    });
  }

  async getLatestIngested(): Promise<ApiResponse> {
    return this.request<ApiResponse>('/api/ingested/latest');
  }

  // AI Narrative Processing
  async processNarrative(text: string): Promise<ApiResponse> {
    return this.request<ApiResponse>('/api/scenarios/narrative', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  }

  // Decision Traces
  async getTrace(contextId: string): Promise<TraceResponse> {
    return this.request<TraceResponse>(`/api/trace/${contextId}`);
  }

  // Room Export/Import
  async exportRoom(contextId: string): Promise<ApiResponse> {
    return this.request<ApiResponse>(`/api/room/export/${contextId}`);
  }

  async importRoom(exportData: any): Promise<ApiResponse> {
    return this.request<ApiResponse>('/api/room/import', {
      method: 'POST',
      body: JSON.stringify({ export_data: exportData }),
    });
  }

  // A2A Protocol (Server-Sent Events)
  createA2AStream(contextId: string, message: string): EventSource {
    const payload = {
      jsonrpc: '2.0',
      method: 'message/stream',
      params: {
        contextId,
        parts: [{ kind: 'text', text: message }]
      },
      id: Date.now()
    };

    const eventSource = new EventSource('/api/bridge/demo/a2a', {
      // Note: EventSource doesn't support POST directly, you'll need to use fetch for A2A
    });

    return eventSource;
  }

  // MCP Protocol
  async beginChatThread(): Promise<{ conversationId: string }> {
    const response = await this.request<{ content: Array<{ text: string }> }>('/api/mcp/begin_chat_thread', {
      method: 'POST',
      body: JSON.stringify({}),
    });
    
    const data = JSON.parse(response.content[0].text);
    return data;
  }

  async sendMessageToChat(conversationId: string, message: string): Promise<any> {
    const response = await this.request<{ content: Array<{ text: string }> }>('/api/mcp/send_message_to_chat_thread', {
      method: 'POST',
      body: JSON.stringify({ conversationId, message }),
    });
    
    return JSON.parse(response.content[0].text);
  }

  async checkReplies(conversationId: string, waitMs?: number): Promise<any> {
    const response = await this.request<{ content: Array<{ text: string }> }>('/api/mcp/check_replies', {
      method: 'POST',
      body: JSON.stringify({ conversationId, waitMs }),
    });
    
    return JSON.parse(response.content[0].text);
  }

  // System Management
  async healthCheck(): Promise<{ status: string }> {
    return this.request<{ status: string }>('/health');
  }

  async resetDemo(): Promise<ApiResponse> {
    return this.request<ApiResponse>('/api/admin/reset', {
      method: 'POST',
    });
  }
}

export const apiService = new ApiService();
export default apiService;