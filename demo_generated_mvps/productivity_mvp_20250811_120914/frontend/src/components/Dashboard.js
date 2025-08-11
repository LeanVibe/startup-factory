import React, { useState, useEffect } from 'react';

function Dashboard() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await fetch('/api/v1/dashboard');
      const data = await response.json();
      setMetrics(data.metrics);
    } catch (error) {
      console.error('Error fetching dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div className="dashboard">
      <h2>Business Metrics</h2>
      
      <div className="metrics-grid">
        <div className="metric-card">
          <h3>Total Users</h3>
          <p>{metrics?.total_users || 0}</p>
        </div>
        
        <div className="metric-card">
          <h3>Monthly Revenue</h3>
          <p>${metrics?.monthly_revenue || 0}</p>
        </div>
        
        <div className="metric-card">
          <h3>Growth Rate</h3>
          <p>{metrics?.growth_rate || 0}%</p>
        </div>
      </div>

      <div className="features-section">
        <h3>Key Features</h3>
        <ul>
                    <li key="0">Time tracking</li>
          <li key="1">Project management</li>
          <li key="2">Team collaboration</li>
          <li key="3">Analytics dashboard</li>
        </ul>
      </div>
    </div>
  );
}

export default Dashboard;
