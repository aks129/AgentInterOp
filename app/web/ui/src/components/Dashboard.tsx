import React from 'react';
import ProtocolSwitcher from './ProtocolSwitcher';
import ScenarioManager from './ScenarioManager';
import FHIRPanel from './FHIRPanel';
import ConversationView from './ConversationView';
import DecisionTrace from './DecisionTrace';
import NarrativeProcessor from './NarrativeProcessor';
import SystemStats from './SystemStats';
import ExportImportHub from './ExportImportHub';

const Dashboard: React.FC = () => {
  return (
    <div className="space-y-8">
      {/* Top Row - Protocol & Scenario Management */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <ProtocolSwitcher />
        <ScenarioManager />
        <SystemStats />
      </div>

      {/* Middle Row - FHIR Integration & Narrative Processing */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <FHIRPanel />
        <NarrativeProcessor />
      </div>

      {/* Bottom Row - Conversation & Decision Tracking */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ConversationView />
        </div>
        <div className="space-y-6">
          <DecisionTrace />
          <ExportImportHub />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;