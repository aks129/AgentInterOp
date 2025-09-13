import React, { useState } from 'react';
import { Database, Search, Download, CheckCircle, AlertCircle, Loader } from 'lucide-react';
import { useApp } from '../contexts/AppContext';

const FHIRPanel: React.FC = () => {
  const { state, actions } = useApp();
  const { fhirConnected, loading } = state;
  const [config, setConfig] = useState({ base: 'https://hapi.fhir.org/baseR4', token: '' });
  const [searchTerm, setSearchTerm] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState<string | null>(null);
  const [patients, setPatients] = useState<any[]>([]);

  const handleTestConnection = async () => {
    await actions.testFhirConnection(config.base, config.token);
  };

  const handleSearch = async () => {
    if (!searchTerm.trim()) return;
    setIsSearching(true);
    try {
      const results = await actions.searchPatients(searchTerm);
      setPatients(results.entry?.map((e: any) => e.resource) || []);
    } catch (error) {
      console.error('Search failed:', error);
    }
    setIsSearching(false);
  };

  const handleIngest = async (patientId: string) => {
    setSelectedPatient(patientId);
    await actions.ingestPatient(patientId);
    setSelectedPatient(null);
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-6 border border-slate-200">
      <div className="flex items-center space-x-2 mb-4">
        <Database className="h-5 w-5 text-medical-blue" />
        <h3 className="text-lg font-semibold text-slate-800">FHIR Integration</h3>
        <div className={`w-2 h-2 rounded-full ${fhirConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
      </div>

      {/* FHIR Server Configuration */}
      <div className="space-y-3 mb-6">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">FHIR Server Base URL</label>
          <input
            type="text"
            value={config.base}
            onChange={(e) => setConfig({ ...config, base: e.target.value })}
            placeholder="https://hapi.fhir.org/baseR4"
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-medical-blue focus:border-transparent"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Access Token (Optional)</label>
          <input
            type="password"
            value={config.token}
            onChange={(e) => setConfig({ ...config, token: e.target.value })}
            placeholder="Bearer token for authentication"
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-medical-blue focus:border-transparent"
          />
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 text-sm">
            {fhirConnected ? (
              <>
                <CheckCircle className="h-4 w-4 text-green-500" />
                <span className="text-green-700">Connected to FHIR server</span>
              </>
            ) : (
              <>
                <AlertCircle className="h-4 w-4 text-orange-500" />
                <span className="text-orange-700">Not connected</span>
              </>
            )}
          </div>
          <button
            onClick={handleTestConnection}
            disabled={loading}
            className="px-3 py-1 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            Test Connection
          </button>
        </div>
      </div>

      {/* Patient Search */}
      <div className="space-y-3">
        <div className="flex space-x-2">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search patients by name..."
            className="flex-1 px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-medical-blue focus:border-transparent"
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button
            onClick={handleSearch}
            disabled={!fhirConnected || isSearching}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            {isSearching ? (
              <Loader className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
            <span>Search</span>
          </button>
        </div>

        {/* Patient Results */}
        {patients.length > 0 && (
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {patients.map((patient) => (
              <div key={patient.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                <div>
                  <p className="font-medium text-sm text-slate-800">
                    {patient.name?.[0]?.given?.join(' ')} {patient.name?.[0]?.family}
                  </p>
                  <p className="text-xs text-slate-600">ID: {patient.id} • DOB: {patient.birthDate}</p>
                </div>
                <button
                  onClick={() => handleIngest(patient.id)}
                  disabled={selectedPatient === patient.id}
                  className="px-3 py-1 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center space-x-1"
                >
                  {selectedPatient === patient.id ? (
                    <Loader className="h-3 w-3 animate-spin" />
                  ) : (
                    <Download className="h-3 w-3" />
                  )}
                  <span>Ingest</span>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default FHIRPanel;