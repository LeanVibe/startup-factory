import React from 'react';
import Dashboard from './components/Dashboard';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>🚀 MVP Dashboard</h1>
        <p>Your startup in action</p>
      </header>
      <main className="container">
        <Dashboard />
      </main>
    </div>
  );
}

export default App;
