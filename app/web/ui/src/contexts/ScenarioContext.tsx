import React, { createContext, useContext, useState, ReactNode } from 'react';

interface Scenario {
  label: string;
  description?: string;
}

interface ScenarioContextType {
  scenarios: Record<string, Scenario>;
  activeScenario: string | null;
  setActiveScenario: (scenario: string) => void;
  isLoading: boolean;
}

const ScenarioContext = createContext<ScenarioContextType | undefined>(undefined);

export const ScenarioProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [scenarios] = useState<Record<string, Scenario>>({
    bcse: { label: 'Breast Cancer Screening (BCS-E)' },
    clinical_trial: { label: 'Clinical Trial Eligibility' },
    referral_specialist: { label: 'Specialist Referral' },
    prior_auth: { label: 'Prior Authorization' },
    custom: { label: 'Custom Scenario' }
  });
  
  const [activeScenario, setActiveScenarioState] = useState<string | null>('bcse');
  const [isLoading, setIsLoading] = useState(false);

  const setActiveScenario = async (scenario: string) => {
    setIsLoading(true);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 500));
    
    setActiveScenarioState(scenario);
    setIsLoading(false);
  };

  return (
    <ScenarioContext.Provider value={{ scenarios, activeScenario, setActiveScenario, isLoading }}>
      {children}
    </ScenarioContext.Provider>
  );
};

export const useScenario = () => {
  const context = useContext(ScenarioContext);
  if (context === undefined) {
    throw new Error('useScenario must be used within a ScenarioProvider');
  }
  return context;
};