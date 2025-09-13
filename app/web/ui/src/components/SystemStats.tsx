import React from 'react';
import { Activity, Clock, CheckCircle, Users } from 'lucide-react';

const SystemStats: React.FC = () => {
  const stats = [
    {
      label: 'Active Sessions',
      value: '3',
      icon: Users,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50'
    },
    {
      label: 'Avg Response Time',
      value: '2.3s',
      icon: Clock,
      color: 'text-green-600',
      bgColor: 'bg-green-50'
    },
    {
      label: 'Success Rate',
      value: '98.7%',
      icon: CheckCircle,
      color: 'text-healthcare-green',
      bgColor: 'bg-green-50'
    }
  ];

  return (
    <div className="bg-white rounded-xl shadow-md p-6 border border-slate-200">
      <div className="flex items-center space-x-2 mb-4">
        <Activity className="h-5 w-5 text-medical-blue" />
        <h3 className="text-lg font-semibold text-slate-800">System Performance</h3>
      </div>

      <div className="space-y-4">
        {stats.map((stat, index) => {
          const IconComponent = stat.icon;
          return (
            <div key={index} className="flex items-center space-x-3">
              <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                <IconComponent className={`h-4 w-4 ${stat.color}`} />
              </div>
              <div className="flex-1">
                <p className="text-sm text-slate-600">{stat.label}</p>
                <p className="text-xl font-semibold text-slate-800">{stat.value}</p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-6 pt-4 border-t border-slate-200">
        <div className="flex items-center space-x-2 text-sm text-green-700">
          <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
          <span>All systems operational</span>
        </div>
      </div>
    </div>
  );
};

export default SystemStats;