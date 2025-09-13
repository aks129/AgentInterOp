import React from 'react';
import Dashboard from './components/Dashboard';
import Header from './components/Header';
import { AppProvider } from './contexts/AppContext';

function App() {
  return (
    <AppProvider>
      <div className="min-h-screen bg-slate-50">
        <Header />
        <main className="container mx-auto px-4 py-8">
          <Dashboard />
        </main>
      </div>
    </AppProvider>
  );
}

export default App;