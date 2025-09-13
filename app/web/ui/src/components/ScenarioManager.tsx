import React from 'react';
import { FileText, CheckCircle, Clock, Users, Shield, Settings } from 'lucide-react';
import { useApp } from '../contexts/AppContext';

const ScenarioManager: React.FC = () => {
  const { state, actions } = useApp();
  const { scenarios, activeScenario, loading } = state;

  const scenarioIcons = {
    bcse: FileText,
    clinical_trial: Users,
    referral_specialist: CheckCircle,
    prior_auth: Shield,
    custom: Settings,
  };

  const scenarioColors = {
    bcse: 'bg-pink-500',
    clinical_trial: 'bg-blue-500',
    referral_specialist: 'bg-green-500',
    prior_auth: 'bg-orange-500',
    custom: 'bg-purple-500',
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-6 border border-slate-200">
      <div className="flex items-center space-x-2 mb-4">
        <Clock className="h-5 w-5 text-healthcare-green" />
        <h3 className="text-lg font-semibold text-slate-800">Clinical Scenarios</h3>
      </div>

      <div className="space-y-2">
        {scenarios && Object.entries(scenarios.scenarios).map(([key, scenario]) => {
          const IconComponent = scenarioIcons[key as keyof typeof scenarioIcons] || Settings;
          const isActive = scenarios?.active === key;
          
          return (
            <button
              key={key}
              onClick={() => actions.activateScenario(key)}
              disabled={loading}
              className={`w-full p-3 rounded-lg border transition-all duration-200 ${
                isActive
                  ? 'border-healthcare-green bg-green-50 shadow-sm'
                  : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
              } ${loading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <div className="flex items-center space-x-3">
                <div className={`p-2 rounded-lg ${scenarioColors[key as keyof typeof scenarioColors]} bg-opacity-10`}>
                  <IconComponent className={`h-4 w-4 ${isActive ? 'text-healthcare-green' : 'text-slate-600'}`} />
                </div>
                <div className="text-left flex-1">
                  <p className={`font-medium text-sm ${isActive ? 'text-healthcare-green' : 'text-slate-800'}`}>
                    {scenario.label}
                  </p>
                </div>
                {isActive && (
                  <CheckCircle className="h-4 w-4 text-healthcare-green" />
                )}
              </div>
            </button>
          );
        })}
      </div>

      {activeScenario && (
        <div className="mt-4 p-4 bg-slate-50 rounded-lg">
          <h4 className="font-medium text-sm text-slate-800 mb-2">Active Scenario</h4>
          <p className="text-xs text-slate-600 leading-relaxed">
            {activeScenario.label} - Ready for eligibility evaluation
          </p>
        </div>
      )}
    </div>
  );
};

export default ScenarioManager;