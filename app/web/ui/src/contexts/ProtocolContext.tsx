import React, { createContext, useContext, useState, ReactNode } from 'react';

interface ProtocolContextType {
  protocol: 'a2a' | 'mcp';
  setProtocol: (protocol: 'a2a' | 'mcp') => Promise<void>;
  isLoading: boolean;
}

const ProtocolContext = createContext<ProtocolContextType | undefined>(undefined);

export const ProtocolProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [protocol, setProtocolState] = useState<'a2a' | 'mcp'>('a2a');
  const [isLoading, setIsLoading] = useState(false);

  const setProtocol = async (newProtocol: 'a2a' | 'mcp') => {
    setIsLoading(true);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    setProtocolState(newProtocol);
    setIsLoading(false);
  };

  return (
    <ProtocolContext.Provider value={{ protocol, setProtocol, isLoading }}>
      {children}
    </ProtocolContext.Provider>
  );
};

export const useProtocol = () => {
  const context = useContext(ProtocolContext);
  if (context === undefined) {
    throw new Error('useProtocol must be used within a ProtocolProvider');
  }
  return context;
};