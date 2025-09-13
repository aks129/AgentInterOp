import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { apiService, Protocol, Scenario, ScenarioList } from '../services/api';

interface AppState {
  protocol: 'a2a' | 'mcp';
  scenarios: ScenarioList | null;
  activeScenario: Scenario | null;
  fhirConnected: boolean;
  loading: boolean;
  error: string | null;
  ingestedData: any | null;
  traces: any[];
}

type AppAction =
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_PROTOCOL'; payload: 'a2a' | 'mcp' }
  | { type: 'SET_SCENARIOS'; payload: ScenarioList }
  | { type: 'SET_ACTIVE_SCENARIO'; payload: Scenario }
  | { type: 'SET_FHIR_CONNECTED'; payload: boolean }
  | { type: 'SET_INGESTED_DATA'; payload: any }
  | { type: 'ADD_TRACE'; payload: any };

const initialState: AppState = {
  protocol: 'a2a',
  scenarios: null,
  activeScenario: null,
  fhirConnected: false,
  loading: false,
  error: null,
  ingestedData: null,
  traces: [],
};

function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload, loading: false };
    case 'SET_PROTOCOL':
      return { ...state, protocol: action.payload };
    case 'SET_SCENARIOS':
      return { ...state, scenarios: action.payload };
    case 'SET_ACTIVE_SCENARIO':
      return { ...state, activeScenario: action.payload };
    case 'SET_FHIR_CONNECTED':
      return { ...state, fhirConnected: action.payload };
    case 'SET_INGESTED_DATA':
      return { ...state, ingestedData: action.payload };
    case 'ADD_TRACE':
      return { ...state, traces: [...state.traces, action.payload] };
    default:
      return state;
  }
}

interface AppContextType {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
  actions: {
    switchProtocol: (protocol: 'a2a' | 'mcp') => Promise<void>;
    loadScenarios: () => Promise<void>;
    activateScenario: (name: string) => Promise<void>;
    testFhirConnection: (base: string, token?: string) => Promise<void>;
    searchPatients: (name: string) => Promise<any>;
    ingestPatient: (patientId: string) => Promise<void>;
    processNarrative: (text: string) => Promise<any>;
    startConversation: (message: string) => Promise<void>;
    resetDemo: () => Promise<void>;
  };
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  // Initialize app data
  useEffect(() => {
    const initializeApp = async () => {
      try {
        dispatch({ type: 'SET_LOADING', payload: true });
        
        // Load current protocol
        const protocolResponse = await apiService.getCurrentProtocol();
        dispatch({ type: 'SET_PROTOCOL', payload: protocolResponse.protocol });
        
        // Load scenarios
        const scenariosResponse = await apiService.getScenarios();
        dispatch({ type: 'SET_SCENARIOS', payload: scenariosResponse });
        
        // Load active scenario
        const activeScenarioResponse = await apiService.getActiveScenario();
        dispatch({ type: 'SET_ACTIVE_SCENARIO', payload: activeScenarioResponse });
        
        dispatch({ type: 'SET_LOADING', payload: false });
      } catch (error) {
        dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : 'Failed to initialize app' });
      }
    };

    initializeApp();
  }, []);

  const actions = {
    switchProtocol: async (protocol: 'a2a' | 'mcp') => {
      try {
        dispatch({ type: 'SET_LOADING', payload: true });
        await apiService.switchProtocol(protocol);
        dispatch({ type: 'SET_PROTOCOL', payload: protocol });
        dispatch({ type: 'SET_LOADING', payload: false });
      } catch (error) {
        dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : 'Failed to switch protocol' });
      }
    },

    loadScenarios: async () => {
      try {
        const response = await apiService.getScenarios();
        dispatch({ type: 'SET_SCENARIOS', payload: response });
      } catch (error) {
        dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : 'Failed to load scenarios' });
      }
    },

    activateScenario: async (name: string) => {
      try {
        dispatch({ type: 'SET_LOADING', payload: true });
        await apiService.activateScenario(name);
        const activeScenario = await apiService.getActiveScenario();
        dispatch({ type: 'SET_ACTIVE_SCENARIO', payload: activeScenario });
        dispatch({ type: 'SET_LOADING', payload: false });
      } catch (error) {
        dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : 'Failed to activate scenario' });
      }
    },

    testFhirConnection: async (base: string, token?: string) => {
      try {
        dispatch({ type: 'SET_LOADING', payload: true });
        await apiService.configureFhir({ base, token });
        await apiService.getFhirCapabilities();
        dispatch({ type: 'SET_FHIR_CONNECTED', payload: true });
        dispatch({ type: 'SET_LOADING', payload: false });
      } catch (error) {
        dispatch({ type: 'SET_FHIR_CONNECTED', payload: false });
        dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : 'FHIR connection failed' });
      }
    },

    searchPatients: async (name: string) => {
      try {
        const response = await apiService.searchPatients({ name });
        return response;
      } catch (error) {
        dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : 'Patient search failed' });
        throw error;
      }
    },

    ingestPatient: async (patientId: string) => {
      try {
        dispatch({ type: 'SET_LOADING', payload: true });
        const patientData = await apiService.getPatientEverything(patientId);
        const ingestResponse = await apiService.ingestPatientData(patientData, patientId);
        dispatch({ type: 'SET_INGESTED_DATA', payload: ingestResponse });
        dispatch({ type: 'SET_LOADING', payload: false });
      } catch (error) {
        dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : 'Patient ingestion failed' });
      }
    },

    processNarrative: async (text: string) => {
      try {
        dispatch({ type: 'SET_LOADING', payload: true });
        const response = await apiService.processNarrative(text);
        dispatch({ type: 'SET_LOADING', payload: false });
        return response;
      } catch (error) {
        dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : 'Narrative processing failed' });
        throw error;
      }
    },

    startConversation: async (message: string) => {
      try {
        dispatch({ type: 'SET_LOADING', payload: true });
        
        if (state.protocol === 'mcp') {
          const chatResponse = await apiService.beginChatThread();
          const messageResponse = await apiService.sendMessageToChat(chatResponse.conversationId, message);
          dispatch({ type: 'ADD_TRACE', payload: { type: 'mcp', data: messageResponse } });
        } else {
          // A2A protocol would use streaming here
          // For now, we'll simulate with a simple message
          dispatch({ type: 'ADD_TRACE', payload: { type: 'a2a', message, timestamp: new Date().toISOString() } });
        }
        
        dispatch({ type: 'SET_LOADING', payload: false });
      } catch (error) {
        dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : 'Conversation failed' });
      }
    },

    resetDemo: async () => {
      try {
        await apiService.resetDemo();
        dispatch({ type: 'SET_INGESTED_DATA', payload: null });
        dispatch({ type: 'ADD_TRACE', payload: { type: 'system', message: 'Demo reset', timestamp: new Date().toISOString() } });
      } catch (error) {
        dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : 'Reset failed' });
      }
    },
  };

  return (
    <AppContext.Provider value={{ state, dispatch, actions }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}

export default AppContext;