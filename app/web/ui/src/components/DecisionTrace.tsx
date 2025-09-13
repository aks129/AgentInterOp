import React, { useState } from 'react';
import { Clock, User, CheckCircle, AlertCircle, Eye } from 'lucide-react';

interface TraceEvent {
  id: string;
  timestamp: Date;
  actor: 'system' | 'user' | 'agent' | 'fhir';
  action: string;
  detail: string;
  status: 'success' | 'warning' | 'error';
}

const DecisionTrace: React.FC = () => {
  const [events] = useState<TraceEvent[]>([
    {
      id: '1',
      timestamp: new Date(Date.now() - 300000),
      actor: 'system',
      action: 'Protocol Switch',
      detail: 'Switched to A2A protocol',
      status: 'success'
    },
    {
      id: '2',
      timestamp: new Date(Date.now() - 240000),
      actor: 'user',
      action: 'Scenario Selection',
      detail: 'Activated BCS-E scenario',
      status: 'success'
    },
    {
      id: '3',
      timestamp: new Date(Date.now() - 180000),
      actor: 'fhir',
      action: 'Patient Data Ingestion',
      detail: 'Patient ID: 123456 processed',
      status: 'success'
    },
    {
      id: '4',
      timestamp: new Date(Date.now() - 120000),
      actor: 'agent',
      action: 'Eligibility Check',
      detail: 'BCS-E criteria evaluated',
      status: 'success'
    },
    {
      id: '5',
      timestamp: new Date(Date.now() - 60000),
      actor: 'system',
      action: 'Decision Generated',
      detail: 'Patient eligible for screening',
      status: 'success'
    }
  ]);

  const getActorIcon = (actor: string) => {
    switch (actor) {
      case 'user': return <User className="h-3 w-3" />;
      case 'agent': return <CheckCircle className="h-3 w-3" />;
      case 'fhir': return <AlertCircle className="h-3 w-3" />;
      default: return <Clock className="h-3 w-3" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'text-green-600 bg-green-50 border-green-200';
      case 'warning': return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'error': return 'text-red-600 bg-red-50 border-red-200';
      default: return 'text-slate-600 bg-slate-50 border-slate-200';
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-6 border border-slate-200">
      <div className="flex items-center space-x-2 mb-4">
        <Eye className="h-5 w-5 text-medical-blue" />
        <h3 className="text-lg font-semibold text-slate-800">Decision Trace</h3>
      </div>

      <div className="space-y-3 max-h-80 overflow-y-auto">
        {events.map((event, index) => (
          <div key={event.id} className="relative">
            {index < events.length - 1 && (
              <div className="absolute left-4 top-8 w-px h-6 bg-slate-200"></div>
            )}
            <div className={`flex items-start space-x-3 p-3 rounded-lg border ${getStatusColor(event.status)}`}>
              <div className="flex-shrink-0 mt-0.5">
                {getActorIcon(event.actor)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2 mb-1">
                  <p className="text-sm font-medium capitalize">{event.actor}</p>
                  <span className="text-xs text-slate-500">
                    {event.timestamp.toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-sm font-medium text-slate-800">{event.action}</p>
                <p className="text-xs text-slate-600 mt-1">{event.detail}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-slate-200">
        <button className="w-full px-3 py-2 text-sm text-medical-blue border border-medical-blue rounded-lg hover:bg-blue-50 transition-colors">
          Export Full Trace
        </button>
      </div>
    </div>
  );
};

export default DecisionTrace;