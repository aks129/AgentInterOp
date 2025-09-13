import React, { createContext, useContext, useState, ReactNode } from 'react';

interface FHIRConfig {
  base: string;
  token: string;
}

interface Patient {
  id: string;
  name?: Array<{ given?: string[]; family?: string }>;
  birthDate?: string;
}

interface FHIRContextType {
  config: FHIRConfig;
  setConfig: (config: FHIRConfig) => void;
  isConnected: boolean;
  patients: Patient[];
  searchPatients: (query: string) => Promise<void>;
  ingestPatient: (patientId: string) => Promise<void>;
}

const FHIRContext = createContext<FHIRContextType | undefined>(undefined);

export const FHIRProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [config, setConfig] = useState<FHIRConfig>({
    base: 'https://hapi.fhir.org/baseR4',
    token: ''
  });
  
  const [isConnected, setIsConnected] = useState(true);
  const [patients, setPatients] = useState<Patient[]>([]);

  const searchPatients = async (query: string) => {
    // Simulate FHIR search
    const mockPatients: Patient[] = [
      {
        id: '123456',
        name: [{ given: ['John'], family: 'Smith' }],
        birthDate: '1968-05-15'
      },
      {
        id: '789012',
        name: [{ given: ['Jane'], family: 'Smith' }],
        birthDate: '1975-08-22'
      },
      {
        id: '345678',
        name: [{ given: ['Robert'], family: 'Smith' }],
        birthDate: '1982-12-03'
      }
    ];
    
    await new Promise(resolve => setTimeout(resolve, 1000));
    setPatients(mockPatients.filter(p => 
      p.name?.[0]?.family?.toLowerCase().includes(query.toLowerCase()) ||
      p.name?.[0]?.given?.[0]?.toLowerCase().includes(query.toLowerCase())
    ));
  };

  const ingestPatient = async (patientId: string) => {
    // Simulate patient data ingestion
    await new Promise(resolve => setTimeout(resolve, 1500));
    console.log(`Ingested patient ${patientId}`);
  };

  return (
    <FHIRContext.Provider value={{ 
      config, 
      setConfig, 
      isConnected, 
      patients, 
      searchPatients, 
      ingestPatient 
    }}>
      {children}
    </FHIRContext.Provider>
  );
};

export const useFHIR = () => {
  const context = useContext(FHIRContext);
  if (context === undefined) {
    throw new Error('useFHIR must be used within a FHIRProvider');
  }
  return context;
};