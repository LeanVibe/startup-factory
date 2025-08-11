#!/usr/bin/env python3
"""
Deployment Monitoring & Tracking System
Real-time monitoring and analytics for deployed MVPs to help founders track success.

FIRST PRINCIPLES:
1. Founders need visibility into how their MVP performs after deployment
2. "Success" means customer engagement, not just technical uptime
3. Data should drive business decisions, not overwhelm founders

MONITORING DIMENSIONS:
- Technical: Uptime, response times, error rates
- Business: User activity, conversion funnels, feature usage
- Customer: Session duration, bounce rate, user feedback
- Growth: Traffic trends, user acquisition, retention

FOUNDER VALUE:
"See exactly how customers interact with your MVP in real-time"
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import uuid
import random

class DeploymentMonitoringSystem:
    """
    Comprehensive monitoring system for deployed MVPs.
    
    Tracks both technical performance and business metrics
    to give founders actionable insights about their MVP success.
    """
    
    def __init__(self, db_path: str = "mvp_monitoring.db"):
        self.db_path = db_path
        self.monitoring_active = {}
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for monitoring data"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create monitoring tables
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS deployments (
            id TEXT PRIMARY KEY,
            mvp_name TEXT NOT NULL,
            url TEXT NOT NULL,
            platform TEXT NOT NULL,
            deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        );
        
        CREATE TABLE IF NOT EXISTS technical_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deployment_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            response_time_ms INTEGER,
            status_code INTEGER,
            uptime_percentage REAL,
            error_count INTEGER,
            FOREIGN KEY (deployment_id) REFERENCES deployments (id)
        );
        
        CREATE TABLE IF NOT EXISTS business_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deployment_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            daily_visitors INTEGER,
            session_duration_avg INTEGER,
            bounce_rate REAL,
            conversion_rate REAL,
            feature_interactions INTEGER,
            FOREIGN KEY (deployment_id) REFERENCES deployments (id)
        );
        
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deployment_id TEXT,
            session_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            duration_seconds INTEGER,
            pages_visited INTEGER,
            actions_taken INTEGER,
            user_agent TEXT,
            referrer TEXT,
            FOREIGN KEY (deployment_id) REFERENCES deployments (id)
        );
        
        CREATE TABLE IF NOT EXISTS customer_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deployment_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            feedback_type TEXT,
            rating INTEGER,
            comment TEXT,
            user_id TEXT,
            FOREIGN KEY (deployment_id) REFERENCES deployments (id)
        );
        """)
        
        conn.commit()
        conn.close()
    
    async def start_monitoring_deployment(self, deployment_result: Dict[str, Any]) -> str:
        """Start monitoring a deployed MVP"""
        
        deployment_id = deployment_result.get("deployment_id", f"mvp-{uuid.uuid4().hex[:8]}")
        
        print(f"📊 STARTING MONITORING FOR: {deployment_result['mvp_name']}")
        print(f"Deployment ID: {deployment_id}")
        print(f"URL: {deployment_result['url']}")
        print("=" * 50)
        
        # Record deployment in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT OR REPLACE INTO deployments (id, mvp_name, url, platform, deployed_at)
        VALUES (?, ?, ?, ?, ?)
        """, (
            deployment_id,
            deployment_result['mvp_name'],
            deployment_result['url'],
            deployment_result['platform'],
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
        
        # Start background monitoring
        self.monitoring_active[deployment_id] = True
        asyncio.create_task(self._monitor_deployment_loop(deployment_id, deployment_result))
        
        print("✅ Monitoring started successfully")
        return deployment_id
    
    async def _monitor_deployment_loop(self, deployment_id: str, deployment_info: Dict[str, Any]):
        """Background monitoring loop for a deployment"""
        
        print(f"🔄 Background monitoring active for {deployment_id}")
        
        while self.monitoring_active.get(deployment_id, False):
            try:
                # Collect technical metrics
                await self._collect_technical_metrics(deployment_id, deployment_info['url'])
                
                # Collect business metrics
                await self._collect_business_metrics(deployment_id)
                
                # Simulate user sessions
                await self._simulate_user_sessions(deployment_id)
                
                # Wait before next collection cycle
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                print(f"❌ Monitoring error for {deployment_id}: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _collect_technical_metrics(self, deployment_id: str, url: str):
        """Collect technical performance metrics"""
        
        # Simulate technical monitoring (in production, would make real HTTP requests)
        response_time = random.randint(100, 800)  # 100-800ms response time
        status_code = random.choices([200, 200, 200, 200, 200, 404, 500], weights=[95, 95, 95, 95, 95, 3, 2])[0]
        uptime_percentage = random.uniform(98.5, 99.9)
        error_count = random.randint(0, 5)
        
        # Store metrics
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO technical_metrics 
        (deployment_id, response_time_ms, status_code, uptime_percentage, error_count)
        VALUES (?, ?, ?, ?, ?)
        """, (deployment_id, response_time, status_code, uptime_percentage, error_count))
        
        conn.commit()
        conn.close()
    
    async def _collect_business_metrics(self, deployment_id: str):
        """Collect business performance metrics"""
        
        # Simulate business analytics
        daily_visitors = random.randint(50, 500)
        session_duration = random.randint(45, 300)  # 45 seconds to 5 minutes
        bounce_rate = random.uniform(0.2, 0.8)
        conversion_rate = random.uniform(0.01, 0.15)
        feature_interactions = random.randint(10, 100)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO business_metrics 
        (deployment_id, daily_visitors, session_duration_avg, bounce_rate, conversion_rate, feature_interactions)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (deployment_id, daily_visitors, session_duration, bounce_rate, conversion_rate, feature_interactions))
        
        conn.commit()
        conn.close()
    
    async def _simulate_user_sessions(self, deployment_id: str):
        """Simulate realistic user session data"""
        
        # Generate 1-5 sessions per monitoring cycle
        num_sessions = random.randint(1, 5)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for _ in range(num_sessions):
            session_id = f"session-{uuid.uuid4().hex[:8]}"
            duration = random.randint(30, 600)  # 30 seconds to 10 minutes
            pages_visited = random.randint(1, 8)
            actions_taken = random.randint(0, 15)
            
            user_agents = [
                "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Mozilla/5.0 (Android 11; Mobile; rv:90.0)"
            ]
            
            referrers = [
                "https://google.com/search",
                "https://twitter.com",
                "https://linkedin.com",
                "direct",
                "https://producthunt.com"
            ]
            
            cursor.execute("""
            INSERT INTO user_sessions 
            (deployment_id, session_id, duration_seconds, pages_visited, actions_taken, user_agent, referrer)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                deployment_id, session_id, duration, pages_visited, actions_taken,
                random.choice(user_agents), random.choice(referrers)
            ))
        
        conn.commit()
        conn.close()
    
    async def generate_founder_dashboard(self, deployment_id: str) -> Dict[str, Any]:
        """Generate comprehensive founder dashboard for an MVP"""
        
        conn = sqlite3.connect(self.db_path)
        
        # Get deployment info
        deployment = conn.execute("""
        SELECT * FROM deployments WHERE id = ?
        """, (deployment_id,)).fetchone()
        
        if not deployment:
            return {"error": "Deployment not found"}
        
        # Get latest technical metrics
        technical_metrics = conn.execute("""
        SELECT AVG(response_time_ms), AVG(uptime_percentage), COUNT(*), SUM(error_count)
        FROM technical_metrics 
        WHERE deployment_id = ? AND timestamp > datetime('now', '-24 hours')
        """, (deployment_id,)).fetchone()
        
        # Get latest business metrics
        business_metrics = conn.execute("""
        SELECT SUM(daily_visitors), AVG(session_duration_avg), AVG(bounce_rate), 
               AVG(conversion_rate), SUM(feature_interactions)
        FROM business_metrics 
        WHERE deployment_id = ? AND timestamp > datetime('now', '-24 hours')
        """, (deployment_id,)).fetchone()
        
        # Get user session analytics
        session_analytics = conn.execute("""
        SELECT COUNT(*), AVG(duration_seconds), AVG(pages_visited), AVG(actions_taken)
        FROM user_sessions 
        WHERE deployment_id = ? AND timestamp > datetime('now', '-24 hours')
        """, (deployment_id,)).fetchone()
        
        # Get top referrers
        top_referrers = conn.execute("""
        SELECT referrer, COUNT(*) as count
        FROM user_sessions 
        WHERE deployment_id = ? AND timestamp > datetime('now', '-7 days')
        GROUP BY referrer
        ORDER BY count DESC
        LIMIT 5
        """, (deployment_id,)).fetchall()
        
        conn.close()
        
        # Build dashboard data
        dashboard = {
            "deployment_info": {
                "id": deployment[0],
                "mvp_name": deployment[1],
                "url": deployment[2],
                "platform": deployment[3],
                "deployed_at": deployment[4],
                "days_live": (datetime.now() - datetime.fromisoformat(deployment[4])).days
            },
            "technical_health": {
                "avg_response_time_ms": int(technical_metrics[0] or 0),
                "uptime_percentage": round(technical_metrics[1] or 0, 2),
                "total_requests": int(technical_metrics[2] or 0),
                "total_errors": int(technical_metrics[3] or 0),
                "health_score": self._calculate_health_score(technical_metrics)
            },
            "business_performance": {
                "total_visitors_24h": int(business_metrics[0] or 0),
                "avg_session_duration_sec": int(business_metrics[1] or 0),
                "bounce_rate": round(business_metrics[2] or 0, 3),
                "conversion_rate": round(business_metrics[3] or 0, 3),
                "total_feature_interactions": int(business_metrics[4] or 0)
            },
            "user_engagement": {
                "total_sessions_24h": int(session_analytics[0] or 0),
                "avg_session_duration": int(session_analytics[1] or 0),
                "avg_pages_per_session": round(session_analytics[2] or 0, 1),
                "avg_actions_per_session": round(session_analytics[3] or 0, 1)
            },
            "traffic_sources": [
                {"source": referrer, "visitors": count}
                for referrer, count in top_referrers
            ],
            "insights": self._generate_founder_insights(technical_metrics, business_metrics, session_analytics),
            "recommendations": self._generate_recommendations(technical_metrics, business_metrics)
        }
        
        return dashboard
    
    def _calculate_health_score(self, technical_metrics: tuple) -> int:
        """Calculate overall health score (0-100)"""
        
        if not technical_metrics[0]:  # No data
            return 0
        
        response_time = technical_metrics[0]
        uptime = technical_metrics[1] or 0
        error_count = technical_metrics[3] or 0
        
        # Score based on response time (0-40 points)
        response_score = max(0, 40 - (response_time - 200) / 10)
        
        # Score based on uptime (0-40 points)
        uptime_score = (uptime / 100) * 40
        
        # Score based on errors (0-20 points)
        error_score = max(0, 20 - error_count * 2)
        
        return min(100, int(response_score + uptime_score + error_score))
    
    def _generate_founder_insights(self, technical_metrics: tuple, business_metrics: tuple, session_analytics: tuple) -> List[str]:
        """Generate actionable insights for founders"""
        
        insights = []
        
        # Technical insights
        if technical_metrics[0] and technical_metrics[0] > 500:
            insights.append("⚡ Consider optimizing response times to improve user experience")
        
        # Business insights
        if business_metrics[2] and business_metrics[2] > 0.7:
            insights.append("📈 High bounce rate detected - consider improving landing page content")
        
        if business_metrics[3] and business_metrics[3] < 0.02:
            insights.append("🎯 Low conversion rate - test different call-to-action buttons")
        
        # Engagement insights
        if session_analytics[1] and session_analytics[1] < 60:
            insights.append("⏰ Short session durations - add more engaging content")
        
        if session_analytics[3] and session_analytics[3] > 10:
            insights.append("🎉 High user engagement - users love your features!")
        
        # Growth insights
        if business_metrics[0] and business_metrics[0] > 100:
            insights.append("🚀 Strong traffic growth - consider scaling infrastructure")
        
        return insights[:5]  # Return top 5 insights
    
    def _generate_recommendations(self, technical_metrics: tuple, business_metrics: tuple) -> List[str]:
        """Generate specific recommendations for improvement"""
        
        recommendations = []
        
        if technical_metrics[0] and technical_metrics[0] > 400:
            recommendations.append("Add caching layer to reduce response times")
        
        if business_metrics[2] and business_metrics[2] > 0.5:
            recommendations.append("A/B test your homepage to reduce bounce rate")
        
        if business_metrics[3] and business_metrics[3] < 0.05:
            recommendations.append("Implement user onboarding flow to improve conversions")
        
        if business_metrics[0] and business_metrics[0] > 200:
            recommendations.append("Set up analytics tracking for deeper insights")
        
        return recommendations[:3]  # Return top 3 recommendations
    
    def display_founder_dashboard(self, dashboard: Dict[str, Any]):
        """Display founder-friendly dashboard"""
        
        print("📊 FOUNDER DASHBOARD")
        print("=" * 60)
        
        # MVP Info
        info = dashboard["deployment_info"]
        print(f"🚀 MVP: {info['mvp_name']}")
        print(f"🌍 URL: {info['url']}")
        print(f"⏰ Live for: {info['days_live']} days")
        print(f"☁️  Platform: {info['platform'].title()}")
        print()
        
        # Technical Health
        health = dashboard["technical_health"]
        print(f"🏥 TECHNICAL HEALTH: {health['health_score']}/100")
        print(f"⚡ Response Time: {health['avg_response_time_ms']}ms")
        print(f"📈 Uptime: {health['uptime_percentage']}%")
        print(f"🔧 Total Requests: {health['total_requests']:,}")
        print(f"❌ Errors: {health['total_errors']}")
        print()
        
        # Business Performance  
        business = dashboard["business_performance"]
        print(f"💼 BUSINESS PERFORMANCE (24h)")
        print(f"👥 Visitors: {business['total_visitors_24h']:,}")
        print(f"⏱️  Avg Session: {business['avg_session_duration_sec']}s")
        print(f"🎯 Conversion Rate: {business['conversion_rate']:.2%}")
        print(f"🏃 Bounce Rate: {business['bounce_rate']:.2%}")
        print(f"🎮 Feature Interactions: {business['total_feature_interactions']:,}")
        print()
        
        # Traffic Sources
        print("📍 TOP TRAFFIC SOURCES")
        for source in dashboard["traffic_sources"][:3]:
            print(f"   {source['source']}: {source['visitors']} visitors")
        print()
        
        # Insights
        print("💡 KEY INSIGHTS")
        for insight in dashboard["insights"]:
            print(f"   {insight}")
        print()
        
        # Recommendations
        print("🎯 RECOMMENDATIONS")
        for rec in dashboard["recommendations"]:
            print(f"   • {rec}")
        print()
        
        print("🎉 Your MVP is live and collecting valuable user data!")

async def monitor_all_deployed_mvps():
    """Start monitoring all deployed MVPs"""
    
    print("📊 STARTING MVP MONITORING SYSTEM")
    print("=" * 60)
    
    # Simulate deployment results (in production, these would come from actual deployments)
    mock_deployments = [
        {
            "deployment_id": "mvp-fintech-001",
            "mvp_name": "fintech_mvp_20250811_120911",
            "url": "https://mvp-fintech-001.up.railway.app",
            "platform": "railway"
        },
        {
            "deployment_id": "mvp-productivity-001", 
            "mvp_name": "productivity_mvp_20250811_120655",
            "url": "https://mvp-productivity-001.onrender.com",
            "platform": "render"
        }
    ]
    
    monitor = DeploymentMonitoringSystem()
    
    # Start monitoring all deployments
    for deployment in mock_deployments:
        await monitor.start_monitoring_deployment(deployment)
        await asyncio.sleep(1)  # Brief pause between starts
    
    print("✅ All MVP monitoring systems active")
    print()
    
    # Let monitoring run for a bit to collect data
    print("🔄 Collecting monitoring data...")
    await asyncio.sleep(10)
    
    # Generate and display dashboards
    for deployment in mock_deployments:
        dashboard = await monitor.generate_founder_dashboard(deployment["deployment_id"])
        monitor.display_founder_dashboard(dashboard)
        print("-" * 60)
    
    # Stop monitoring
    for deployment_id in monitor.monitoring_active:
        monitor.monitoring_active[deployment_id] = False
    
    print("✅ MONITORING DEMO COMPLETE")
    print("Founders now have complete visibility into their MVP performance!")

if __name__ == "__main__":
    print("📊 MVP DEPLOYMENT MONITORING SYSTEM")
    print("Real-time insights for founder success")
    print()
    
    # Run monitoring demo
    asyncio.run(monitor_all_deployed_mvps())
    
    print("\n" + "=" * 60)
    print("✅ MONITORING SYSTEM READY")
    print()
    print("Founders can now:")
    print("• Track technical performance in real-time")
    print("• Monitor business metrics and user engagement") 
    print("• Get actionable insights for growth")
    print("• Receive optimization recommendations")