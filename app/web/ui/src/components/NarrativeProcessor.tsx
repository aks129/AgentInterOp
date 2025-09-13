import React, { useState } from 'react';
import { Brain, FileText, ArrowRight, Loader } from 'lucide-react';

const NarrativeProcessor: React.FC = () => {
  const [narrative, setNarrative] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleProcess = async () => {
    if (!narrative.trim()) return;
    
    setIsProcessing(true);
    
    // Simulate API call
    setTimeout(() => {
      setResult({
        generated_schema: {
          cpt: "72148",
          diagnosis: "M54.5",
          documentation: ["PT_plan.pdf", "imaging_report.pdf"],
          site_of_service: "11"
        },
        confidence: 0.95,
        extracted_entities: ["lumbar spine", "chronic pain", "MRI scan", "physical therapy"]
      });
      setIsProcessing(false);
    }, 2000);
  };

  const exampleText = `Patient John Smith, age 45, requires MRI scan of lumbar spine due to chronic lower back pain persisting for 6 months. Conservative treatments including physical therapy and medication have failed. Patient reports pain level 7/10, worse with prolonged sitting. No neurological deficits noted on examination.`;

  return (
    <div className="bg-white rounded-xl shadow-md p-6 border border-slate-200">
      <div className="flex items-center space-x-2 mb-4">
        <Brain className="h-5 w-5 text-purple-600" />
        <h3 className="text-lg font-semibold text-slate-800">AI Narrative Processing</h3>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">
            Clinical Narrative
          </label>
          <textarea
            value={narrative}
            onChange={(e) => setNarrative(e.target.value)}
            placeholder={exampleText}
            rows={6}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
          />
        </div>

        <div className="flex space-x-2">
          <button
            onClick={() => setNarrative(exampleText)}
            className="px-3 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50"
          >
            Use Example
          </button>
          <button
            onClick={handleProcess}
            disabled={!narrative.trim() || isProcessing}
            className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
          >
            {isProcessing ? (
              <>
                <Loader className="h-4 w-4 animate-spin" />
                <span>Processing...</span>
              </>
            ) : (
              <>
                <ArrowRight className="h-4 w-4" />
                <span>Convert to Structured Data</span>
              </>
            )}
          </button>
        </div>

        {result && (
          <div className="mt-4 p-4 bg-purple-50 rounded-lg">
            <h4 className="font-medium text-sm text-slate-800 mb-2 flex items-center space-x-2">
              <FileText className="h-4 w-4" />
              <span>Structured Output</span>
              <span className="ml-auto text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
                {Math.round(result.confidence * 100)}% confidence
              </span>
            </h4>
            <div className="bg-white rounded p-3 text-sm font-mono">
              <pre className="whitespace-pre-wrap text-slate-700">
                {JSON.stringify(result.generated_schema, null, 2)}
              </pre>
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              {result.extracted_entities.map((entity: string, index: number) => (
                <span key={index} className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded-full">
                  {entity}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default NarrativeProcessor;