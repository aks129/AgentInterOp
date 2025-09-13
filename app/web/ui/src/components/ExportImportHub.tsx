import React, { useState } from 'react';
import { Download, Upload, FileJson, Share } from 'lucide-react';

const ExportImportHub: React.FC = () => {
  const [exportFormat, setExportFormat] = useState<'json' | 'csv'>('json');

  const handleExport = () => {
    const data = {
      contextId: 'ctx_' + Date.now(),
      scenario: 'bcse',
      timestamp: new Date().toISOString(),
      session_data: {
        protocol: 'a2a',
        decisions: ['eligible'],
        trace_events: 5
      }
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `healthcare_session_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-6 border border-slate-200">
      <div className="flex items-center space-x-2 mb-4">
        <Share className="h-5 w-5 text-medical-blue" />
        <h3 className="text-lg font-semibold text-slate-800">Export/Import</h3>
      </div>

      <div className="space-y-4">
        {/* Export Section */}
        <div>
          <h4 className="text-sm font-medium text-slate-700 mb-2">Export Session</h4>
          <div className="flex space-x-2 mb-3">
            <button
              onClick={() => setExportFormat('json')}
              className={`px-3 py-1 text-xs rounded-lg border ${
                exportFormat === 'json'
                  ? 'border-medical-blue bg-blue-50 text-medical-blue'
                  : 'border-slate-300 text-slate-600 hover:bg-slate-50'
              }`}
            >
              JSON
            </button>
            <button
              onClick={() => setExportFormat('csv')}
              className={`px-3 py-1 text-xs rounded-lg border ${
                exportFormat === 'csv'
                  ? 'border-medical-blue bg-blue-50 text-medical-blue'
                  : 'border-slate-300 text-slate-600 hover:bg-slate-50'
              }`}
            >
              CSV
            </button>
          </div>
          <button
            onClick={handleExport}
            className="w-full px-3 py-2 bg-medical-blue text-white text-sm rounded-lg hover:bg-blue-700 flex items-center justify-center space-x-2"
          >
            <Download className="h-4 w-4" />
            <span>Export Current Session</span>
          </button>
        </div>

        {/* Import Section */}
        <div>
          <h4 className="text-sm font-medium text-slate-700 mb-2">Import Session</h4>
          <div className="border-2 border-dashed border-slate-300 rounded-lg p-6 text-center hover:border-medical-blue hover:bg-blue-50 transition-colors cursor-pointer">
            <FileJson className="h-8 w-8 text-slate-400 mx-auto mb-2" />
            <p className="text-sm text-slate-600 mb-2">Drop session file here</p>
            <button className="px-3 py-1 text-sm text-medical-blue border border-medical-blue rounded-lg hover:bg-blue-50 flex items-center space-x-1 mx-auto">
              <Upload className="h-3 w-3" />
              <span>Browse Files</span>
            </button>
          </div>
        </div>

        <div className="text-xs text-slate-500 bg-slate-50 p-3 rounded-lg">
          <p className="font-medium mb-1">Supported formats:</p>
          <p>• Healthcare session JSON</p>
          <p>• FHIR Bundle resources</p>
          <p>• Decision trace exports</p>
        </div>
      </div>
    </div>
  );
};

export default ExportImportHub;