import React from 'react';
import { Activity, Heart, Shield } from 'lucide-react';
import { useApp } from '../contexts/AppContext';

const Header: React.FC = () => {
  const { state } = useApp();

  return (
    <header className="bg-blue-900 text-white shadow-lg">
      <div className="container mx-auto px-4 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="bg-white/10 p-2 rounded-lg">
              <Heart className="h-8 w-8 text-green-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">Healthcare Interoperability Demo</h1>
              <p className="text-blue-200">Multi-Agent Clinical Decision Support • HL7 WGM 2025</p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 bg-white/10 px-3 py-2 rounded-lg">
              <Activity className={`h-4 w-4 ${state.loading ? 'text-yellow-400' : 'text-green-400'}`} />
              <span className="text-sm">{state.loading ? 'Processing...' : 'System Ready'}</span>
            </div>
            <div className="flex items-center space-x-2 bg-white/10 px-3 py-2 rounded-lg">
              <Shield className={`h-4 w-4 ${state.fhirConnected ? 'text-green-400' : 'text-gray-400'}`} />
              <span className="text-sm">FHIR {state.fhirConnected ? 'Connected' : 'Disconnected'}</span>
            </div>
            <div className="bg-white/10 px-3 py-2 rounded-lg">
              <span className="text-sm font-medium">Protocol: {state.protocol.toUpperCase()}</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;