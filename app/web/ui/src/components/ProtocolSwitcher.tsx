import React from 'react';
import { ArrowLeftRight, Zap, Network } from 'lucide-react';
import { useApp } from '../contexts/AppContext';

const ProtocolSwitcher: React.FC = () => {
  const { state, actions } = useApp();
  const { protocol, loading } = state;

  const protocols = [
    {
      id: 'a2a',
      name: 'Agent-to-Agent (A2A)',
      description: 'Direct streaming communication',
      icon: ArrowLeftRight,
      color: 'bg-blue-500',
    },
    {
      id: 'mcp',
      name: 'Model Context Protocol',
      description: 'Standardized model communication',
      icon: Network,
      color: 'bg-purple-500',
    }
  ];

  return (
    <div className="bg-white rounded-xl shadow-md p-6 border border-slate-200">
      <div className="flex items-center space-x-2 mb-4">
        <Zap className="h-5 w-5 text-medical-blue" />
        <h3 className="text-lg font-semibold text-slate-800">Protocol Selection</h3>
      </div>
      
      <div className="space-y-3">
        {protocols.map((p) => {
          const IconComponent = p.icon;
          const isActive = protocol === p.id;
          
          return (
            <button
              key={p.id}
              onClick={() => actions.switchProtocol(p.id as 'a2a' | 'mcp')}
              disabled={loading}
              className={`w-full p-4 rounded-lg border-2 transition-all duration-200 ${
                isActive
                  ? 'border-medical-blue bg-blue-50 shadow-md'
                  : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
              } ${loading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <div className="flex items-center space-x-3">
                <div className={`p-2 rounded-lg ${p.color} bg-opacity-10`}>
                  <IconComponent className={`h-5 w-5 ${isActive ? 'text-medical-blue' : 'text-slate-600'}`} />
                </div>
                <div className="text-left flex-1">
                  <h4 className={`font-medium ${isActive ? 'text-medical-blue' : 'text-slate-800'}`}>
                    {p.name}
                  </h4>
                  <p className="text-sm text-slate-600">{p.description}</p>
                </div>
                {isActive && (
                  <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {loading && (
        <div className="mt-4 flex items-center justify-center space-x-2 text-sm text-slate-600">
          <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <span>Switching protocol...</span>
        </div>
      )}
    </div>
  );
};

export default ProtocolSwitcher;