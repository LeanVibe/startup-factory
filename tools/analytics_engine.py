#!/usr/bin/env python3
"""
Analytics Engine for Startup Factory Platform
Provides business intelligence, performance analytics, and optimization recommendations
"""

import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import logging
import asyncio
import statistics
from collections import defaultdict, Counter
import warnings

# Suppress pandas warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class StartupMetadata:
    """Metadata for a startup project"""
    id: str
    name: str
    industry: str
    category: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    status: str = "pending"
    duration_minutes: Optional[float] = None
    resource_usage: Dict[str, Any] = None
    api_costs: Dict[str, float] = None
    success_score: Optional[float] = None
    bottlenecks: List[str] = None

@dataclass
class PerformanceMetrics:
    """Performance metrics for analysis"""
    timestamp: datetime
    memory_usage_mb: float
    cpu_percent: float
    concurrent_startups: int
    api_call_count: int
    error_count: int
    response_time_ms: float

@dataclass
class BusinessIntelligence:
    """Business intelligence insights"""
    total_startups: int
    success_rate: float
    avg_creation_time: float
    cost_per_startup: float
    most_successful_industries: List[str]
    common_bottlenecks: List[str]
    optimization_recommendations: List[str]
    roi_analysis: Dict[str, float]

class AnalyticsDatabase:
    """Database for storing analytics data"""
    
    def __init__(self, db_path: Path = Path("analytics.db")):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Configure datetime adapters to avoid deprecation warnings
            sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
            sqlite3.register_converter("TIMESTAMP", lambda val: datetime.fromisoformat(val.decode()))
            # Startups table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS startups (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    industry TEXT,
                    category TEXT,
                    created_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    status TEXT,
                    duration_minutes REAL,
                    resource_usage TEXT,
                    api_costs TEXT,
                    success_score REAL,
                    bottlenecks TEXT
                )
            """)
            
            # Performance metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    memory_usage_mb REAL,
                    cpu_percent REAL,
                    concurrent_startups INTEGER,
                    api_call_count INTEGER,
                    error_count INTEGER,
                    response_time_ms REAL
                )
            """)
            
            # Events table for tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    event_type TEXT,
                    startup_id TEXT,
                    phase TEXT,
                    details TEXT
                )
            """)
    
    def store_startup(self, startup: StartupMetadata):
        """Store startup metadata"""
        with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO startups 
                (id, name, industry, category, created_at, completed_at, status, 
                 duration_minutes, resource_usage, api_costs, success_score, bottlenecks)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                startup.id, startup.name, startup.industry, startup.category,
                startup.created_at, startup.completed_at, startup.status,
                startup.duration_minutes,
                json.dumps(startup.resource_usage) if startup.resource_usage else None,
                json.dumps(startup.api_costs) if startup.api_costs else None,
                startup.success_score,
                json.dumps(startup.bottlenecks) if startup.bottlenecks else None
            ))
    
    def store_performance_metric(self, metric: PerformanceMetrics):
        """Store performance metric"""
        with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
            conn.execute("""
                INSERT INTO performance_metrics 
                (timestamp, memory_usage_mb, cpu_percent, concurrent_startups, 
                 api_call_count, error_count, response_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                metric.timestamp, metric.memory_usage_mb, metric.cpu_percent,
                metric.concurrent_startups, metric.api_call_count,
                metric.error_count, metric.response_time_ms
            ))
    
    def log_event(self, event_type: str, startup_id: str = None, phase: str = None, details: Dict = None):
        """Log an event"""
        with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
            conn.execute("""
                INSERT INTO events (timestamp, event_type, startup_id, phase, details)
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now(), event_type, startup_id, phase,
                json.dumps(details) if details else None
            ))
    
    def get_startups_dataframe(self) -> pd.DataFrame:
        """Get startups as pandas DataFrame"""
        with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
            return pd.read_sql_query("SELECT * FROM startups", conn)
    
    def get_performance_dataframe(self) -> pd.DataFrame:
        """Get performance metrics as pandas DataFrame"""
        with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
            return pd.read_sql_query("SELECT * FROM performance_metrics", conn)
    
    def get_events_dataframe(self) -> pd.DataFrame:
        """Get events as pandas DataFrame"""
        with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
            return pd.read_sql_query("SELECT * FROM events", conn)

class PerformanceAnalyzer:
    """Analyzes performance patterns and bottlenecks"""
    
    def __init__(self, db: AnalyticsDatabase):
        self.db = db
    
    def analyze_startup_performance(self) -> Dict[str, Any]:
        """Analyze startup creation performance"""
        df = self.db.get_startups_dataframe()
        
        if df.empty:
            return {"error": "No startup data available"}
        
        # Convert timestamps
        df['created_at'] = pd.to_datetime(df['created_at'])
        df['completed_at'] = pd.to_datetime(df['completed_at'])
        
        # Calculate completion times
        completed_startups = df[df['status'] == 'completed'].copy()
        
        if not completed_startups.empty:
            completed_startups['duration_calculated'] = (
                completed_startups['completed_at'] - completed_startups['created_at']
            ).dt.total_seconds() / 60  # Convert to minutes
        
        analysis = {
            'total_startups': len(df),
            'completed_startups': len(completed_startups),
            'failed_startups': len(df[df['status'] == 'failed']),
            'in_progress_startups': len(df[df['status'].isin(['running', 'pending'])]),
            'success_rate': len(completed_startups) / len(df) if len(df) > 0 else 0,
        }
        
        if not completed_startups.empty:
            durations = completed_startups['duration_calculated'].dropna()
            if not durations.empty:
                analysis.update({
                    'avg_completion_time_minutes': durations.mean(),
                    'median_completion_time_minutes': durations.median(),
                    'min_completion_time_minutes': durations.min(),
                    'max_completion_time_minutes': durations.max(),
                    'std_completion_time_minutes': durations.std(),
                    'target_achievement': (durations <= 30).mean()  # <30 minutes target
                })
        
        return analysis
    
    def analyze_resource_usage(self) -> Dict[str, Any]:
        """Analyze resource usage patterns"""
        perf_df = self.db.get_performance_dataframe()
        
        if perf_df.empty:
            return {"error": "No performance data available"}
        
        perf_df['timestamp'] = pd.to_datetime(perf_df['timestamp'])
        
        # Recent performance (last hour)
        recent_cutoff = datetime.now() - timedelta(hours=1)
        recent_df = perf_df[perf_df['timestamp'] >= recent_cutoff]
        
        analysis = {}
        
        for df, label in [(perf_df, 'overall'), (recent_df, 'recent')]:
            if not df.empty:
                analysis[label] = {
                    'avg_memory_usage_mb': df['memory_usage_mb'].mean(),
                    'max_memory_usage_mb': df['memory_usage_mb'].max(),
                    'avg_cpu_percent': df['cpu_percent'].mean(),
                    'max_cpu_percent': df['cpu_percent'].max(),
                    'avg_concurrent_startups': df['concurrent_startups'].mean(),
                    'max_concurrent_startups': df['concurrent_startups'].max(),
                    'avg_response_time_ms': df['response_time_ms'].mean(),
                    'error_rate': df['error_count'].sum() / len(df) if len(df) > 0 else 0
                }
            elif label == 'recent':
                # Always include 'recent' section for consistent API, even if no recent data
                analysis[label] = {
                    'avg_memory_usage_mb': 0.0,
                    'max_memory_usage_mb': 0.0,
                    'avg_cpu_percent': 0.0,
                    'max_cpu_percent': 0.0,
                    'avg_concurrent_startups': 0.0,
                    'max_concurrent_startups': 0.0,
                    'avg_response_time_ms': 0.0,
                    'error_rate': 0.0,
                    'note': 'No recent data available'
                }
        
        return analysis
    
    def identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        # Analyze startup data
        startup_analysis = self.analyze_startup_performance()
        
        # Check completion time bottleneck
        if startup_analysis.get('avg_completion_time_minutes', 0) > 30:
            bottlenecks.append({
                'type': 'completion_time',
                'severity': 'high',
                'description': f"Average completion time ({startup_analysis['avg_completion_time_minutes']:.1f} min) exceeds 30-minute target",
                'recommendation': 'Implement parallel processing and API caching'
            })
        
        # Check success rate bottleneck
        if startup_analysis.get('success_rate', 1) < 0.9:
            bottlenecks.append({
                'type': 'success_rate',
                'severity': 'high',
                'description': f"Success rate ({startup_analysis['success_rate']:.1%}) below 90% target",
                'recommendation': 'Improve error handling and retry mechanisms'
            })
        
        # Analyze resource usage
        resource_analysis = self.analyze_resource_usage()
        
        if 'recent' in resource_analysis:
            recent = resource_analysis['recent']
            
            # Memory bottleneck
            if recent.get('avg_memory_usage_mb', 0) > 4000:  # 4GB
                bottlenecks.append({
                    'type': 'memory_usage',
                    'severity': 'medium',
                    'description': f"High memory usage ({recent['avg_memory_usage_mb']:.0f}MB)",
                    'recommendation': 'Implement memory pooling and garbage collection optimization'
                })
            
            # CPU bottleneck
            if recent.get('avg_cpu_percent', 0) > 70:
                bottlenecks.append({
                    'type': 'cpu_usage',
                    'severity': 'medium',
                    'description': f"High CPU usage ({recent['avg_cpu_percent']:.1f}%)",
                    'recommendation': 'Optimize algorithms and implement parallel processing'
                })
        
        return bottlenecks
    
    def analyze_trends(self, days: int = 7) -> Dict[str, Any]:
        """Analyze performance trends over time"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Startup trends
        startup_df = self.db.get_startups_dataframe()
        startup_df['created_at'] = pd.to_datetime(startup_df['created_at'])
        recent_startups = startup_df[startup_df['created_at'] >= cutoff_date]
        
        # Performance trends
        perf_df = self.db.get_performance_dataframe()
        perf_df['timestamp'] = pd.to_datetime(perf_df['timestamp'])
        recent_perf = perf_df[perf_df['timestamp'] >= cutoff_date]
        
        trends = {
            'period_days': days,
            'startups_created': len(recent_startups),
            'daily_startup_rate': len(recent_startups) / days if days > 0 else 0
        }
        
        if not recent_perf.empty:
            # Group by day for trend analysis
            daily_perf = recent_perf.set_index('timestamp').resample('D').agg({
                'memory_usage_mb': 'mean',
                'cpu_percent': 'mean',
                'concurrent_startups': 'mean',
                'response_time_ms': 'mean'
            })
            
            trends.update({
                'memory_trend': self._calculate_trend(daily_perf['memory_usage_mb'].dropna()),
                'cpu_trend': self._calculate_trend(daily_perf['cpu_percent'].dropna()),
                'response_time_trend': self._calculate_trend(daily_perf['response_time_ms'].dropna())
            })
        
        return trends
    
    def _calculate_trend(self, series: pd.Series) -> str:
        """Calculate trend direction (improving/degrading/stable)"""
        if len(series) < 2:
            return "insufficient_data"
        
        # Use linear regression to determine trend
        x = np.arange(len(series))
        slope = np.polyfit(x, series, 1)[0]
        
        if slope > 0.1:
            return "degrading"
        elif slope < -0.1:
            return "improving"
        else:
            return "stable"

class BusinessIntelligenceEngine:
    """Generates business intelligence insights"""
    
    def __init__(self, db: AnalyticsDatabase):
        self.db = db
        self.performance_analyzer = PerformanceAnalyzer(db)
    
    def generate_roi_analysis(self) -> Dict[str, Any]:
        """Generate ROI analysis"""
        startup_df = self.db.get_startups_dataframe()
        
        if startup_df.empty:
            return {"error": "No data available for ROI analysis"}
        
        # Parse API costs
        total_api_costs = 0
        startup_count = len(startup_df)
        
        for _, row in startup_df.iterrows():
            if row['api_costs']:
                try:
                    costs = json.loads(row['api_costs'])
                    total_api_costs += sum(costs.values())
                except:
                    pass
        
        # Estimated savings calculations
        manual_cost_per_startup = 150  # $150 for manual setup
        manual_time_hours = 8  # 8 hours manual setup
        hourly_rate = 100  # $100/hour consultant rate
        
        roi_analysis = {
            'total_startups_analyzed': startup_count,
            'total_api_costs': total_api_costs,
            'avg_api_cost_per_startup': total_api_costs / startup_count if startup_count > 0 else 0,
            'manual_cost_equivalent': startup_count * manual_cost_per_startup,
            'time_saved_hours': startup_count * manual_time_hours * 0.95,  # 95% time reduction
            'cost_savings': (startup_count * manual_cost_per_startup) - total_api_costs,
            'roi_percentage': ((startup_count * manual_cost_per_startup) - total_api_costs) / total_api_costs * 100 if total_api_costs > 0 else 0
        }
        
        return roi_analysis
    
    def analyze_industry_success_patterns(self) -> Dict[str, Any]:
        """Analyze success patterns by industry"""
        df = self.db.get_startups_dataframe()
        
        if df.empty:
            return {"error": "No data available"}
        
        # Group by industry
        industry_stats = df.groupby('industry').agg({
            'status': lambda x: (x == 'completed').mean(),  # Success rate
            'duration_minutes': 'mean',
            'success_score': 'mean'
        }).round(3)
        
        industry_stats.columns = ['success_rate', 'avg_duration_minutes', 'avg_success_score']
        
        # Add startup counts
        industry_counts = df['industry'].value_counts()
        industry_stats['startup_count'] = industry_counts
        
        # Sort by success rate
        industry_stats = industry_stats.sort_values('success_rate', ascending=False)
        
        return {
            'industry_performance': industry_stats.to_dict('index'),
            'most_successful_industries': industry_stats.head(3).index.tolist(),
            'least_successful_industries': industry_stats.tail(3).index.tolist()
        }
    
    def generate_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Get current performance
        perf_analysis = self.performance_analyzer.analyze_startup_performance()
        bottlenecks = self.performance_analyzer.identify_bottlenecks()
        
        # Completion time optimization
        if perf_analysis.get('avg_completion_time_minutes', 0) > 30:
            recommendations.append({
                'category': 'performance',
                'priority': 'high',
                'title': 'Reduce Startup Creation Time',
                'description': 'Implement parallel API calls and response caching',
                'expected_improvement': '40-60% time reduction',
                'implementation_effort': 'medium',
                'estimated_cost': '$2,000'
            })
        
        # Memory optimization
        resource_analysis = self.performance_analyzer.analyze_resource_usage()
        if 'recent' in resource_analysis and resource_analysis['recent'].get('avg_memory_usage_mb', 0) > 2000:
            recommendations.append({
                'category': 'resource',
                'priority': 'medium',
                'title': 'Optimize Memory Usage',
                'description': 'Implement memory pooling and efficient data structures',
                'expected_improvement': '30-50% memory reduction',
                'implementation_effort': 'medium',
                'estimated_cost': '$1,500'
            })
        
        # Success rate optimization
        if perf_analysis.get('success_rate', 1) < 0.9:
            recommendations.append({
                'category': 'reliability',
                'priority': 'high',
                'title': 'Improve Success Rate',
                'description': 'Enhanced error handling and retry mechanisms',
                'expected_improvement': '10-15% success rate increase',
                'implementation_effort': 'low',
                'estimated_cost': '$500'
            })
        
        # Concurrent processing
        if resource_analysis.get('overall', {}).get('max_concurrent_startups', 0) < 5:
            recommendations.append({
                'category': 'scalability',
                'priority': 'high',
                'title': 'Enable 5 Concurrent Startups',
                'description': 'Implement resource isolation and dynamic allocation',
                'expected_improvement': '5x throughput increase',
                'implementation_effort': 'high',
                'estimated_cost': '$3,000'
            })
        
        return recommendations
    
    def generate_comprehensive_report(self) -> BusinessIntelligence:
        """Generate comprehensive business intelligence report"""
        startup_perf = self.performance_analyzer.analyze_startup_performance()
        roi_analysis = self.generate_roi_analysis()
        industry_analysis = self.analyze_industry_success_patterns()
        recommendations = self.generate_optimization_recommendations()
        bottlenecks = self.performance_analyzer.identify_bottlenecks()
        
        return BusinessIntelligence(
            total_startups=startup_perf.get('total_startups', 0),
            success_rate=startup_perf.get('success_rate', 0),
            avg_creation_time=startup_perf.get('avg_completion_time_minutes', 0),
            cost_per_startup=roi_analysis.get('avg_api_cost_per_startup', 0),
            most_successful_industries=industry_analysis.get('most_successful_industries', []),
            common_bottlenecks=[b['description'] for b in bottlenecks],
            optimization_recommendations=[r['title'] for r in recommendations],
            roi_analysis=roi_analysis
        )

class AnalyticsEngine:
    """Main analytics engine controller"""
    
    def __init__(self, db_path: Path = Path("analytics.db")):
        self.db = AnalyticsDatabase(db_path)
        self.bi_engine = BusinessIntelligenceEngine(self.db)
        self.performance_analyzer = PerformanceAnalyzer(self.db)
    
    def track_startup_creation(self, startup_data: Dict[str, Any]):
        """Track a startup creation event"""
        startup = StartupMetadata(
            id=startup_data['id'],
            name=startup_data['name'],
            industry=startup_data.get('industry', 'Unknown'),
            category=startup_data.get('category', 'Unknown'),
            created_at=datetime.fromisoformat(startup_data['created_at']),
            completed_at=datetime.fromisoformat(startup_data['completed_at']) if startup_data.get('completed_at') else None,
            status=startup_data.get('status', 'pending'),
            duration_minutes=startup_data.get('duration_minutes'),
            resource_usage=startup_data.get('resource_usage'),
            api_costs=startup_data.get('api_costs'),
            success_score=startup_data.get('success_score'),
            bottlenecks=startup_data.get('bottlenecks')
        )
        
        self.db.store_startup(startup)
        self.db.log_event('startup_tracked', startup.id)
    
    def track_performance_metric(self, metric_data: Dict[str, Any]):
        """Track a performance metric"""
        metric = PerformanceMetrics(
            timestamp=datetime.fromisoformat(metric_data['timestamp']),
            memory_usage_mb=metric_data.get('memory_usage_mb', 0),
            cpu_percent=metric_data.get('cpu_percent', 0),
            concurrent_startups=metric_data.get('concurrent_startups', 0),
            api_call_count=metric_data.get('api_call_count', 0),
            error_count=metric_data.get('error_count', 0),
            response_time_ms=metric_data.get('response_time_ms', 0)
        )
        
        self.db.store_performance_metric(metric)
    
    def generate_report(self, format: str = 'json') -> Dict[str, Any]:
        """Generate analytics report"""
        report = self.bi_engine.generate_comprehensive_report()
        
        if format == 'json':
            return asdict(report)
        elif format == 'summary':
            return self._generate_summary_report(report)
        else:
            return asdict(report)
    
    def _generate_summary_report(self, report: BusinessIntelligence) -> str:
        """Generate human-readable summary report"""
        summary = f"""
📊 Startup Factory Analytics Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎯 Key Performance Metrics:
• Total Startups: {report.total_startups}
• Success Rate: {report.success_rate:.1%}
• Average Creation Time: {report.avg_creation_time:.1f} minutes
• Cost per Startup: ${report.cost_per_startup:.2f}

🏆 Top Performing Industries:
{chr(10).join(f"• {industry}" for industry in report.most_successful_industries[:3])}

⚠️ Common Bottlenecks:
{chr(10).join(f"• {bottleneck}" for bottleneck in report.common_bottlenecks[:3])}

💡 Top Recommendations:
{chr(10).join(f"• {rec}" for rec in report.optimization_recommendations[:3])}

💰 ROI Analysis:
• Total Cost Savings: ${report.roi_analysis.get('cost_savings', 0):,.2f}
• ROI: {report.roi_analysis.get('roi_percentage', 0):.1f}%
• Time Saved: {report.roi_analysis.get('time_saved_hours', 0):.0f} hours
        """
        
        return summary.strip()
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time analytics metrics"""
        return {
            'timestamp': datetime.now().isoformat(),
            'performance': self.performance_analyzer.analyze_startup_performance(),
            'resource_usage': self.performance_analyzer.analyze_resource_usage(),
            'bottlenecks': self.performance_analyzer.identify_bottlenecks(),
            'trends': self.performance_analyzer.analyze_trends(days=1)  # Last 24 hours
        }
    
    def simulate_data(self):
        """Simulate analytics data for testing"""
        # Simulate some startup data
        industries = ['FinTech', 'HealthTech', 'EdTech', 'PropTech', 'RetailTech']
        statuses = ['completed', 'completed', 'completed', 'failed', 'running']
        
        for i in range(20):
            startup_data = {
                'id': f'startup_{i+1}',
                'name': f'Startup {i+1}',
                'industry': np.random.choice(industries),
                'category': 'B2B SaaS',
                'created_at': (datetime.now() - timedelta(days=np.random.randint(1, 30))).isoformat(),
                'status': np.random.choice(statuses),
                'duration_minutes': np.random.uniform(15, 45) if np.random.choice(statuses) == 'completed' else None,
                'api_costs': {'openai': np.random.uniform(0.1, 0.5), 'anthropic': np.random.uniform(0.2, 0.8)},
                'success_score': np.random.uniform(0.7, 1.0)
            }
            
            if startup_data['status'] == 'completed' and startup_data.get('duration_minutes'):
                startup_data['completed_at'] = (datetime.fromisoformat(startup_data['created_at']) + 
                                               timedelta(minutes=startup_data['duration_minutes'])).isoformat()
            
            self.track_startup_creation(startup_data)
        
        # Simulate performance metrics
        for i in range(100):
            metric_data = {
                'timestamp': (datetime.now() - timedelta(hours=np.random.randint(0, 24))).isoformat(),
                'memory_usage_mb': np.random.uniform(1000, 4000),
                'cpu_percent': np.random.uniform(10, 80),
                'concurrent_startups': np.random.randint(0, 5),
                'api_call_count': np.random.randint(10, 100),
                'error_count': np.random.randint(0, 5),
                'response_time_ms': np.random.uniform(100, 2000)
            }
            
            self.track_performance_metric(metric_data)

def main():
    """Main function for testing"""
    print("📊 Startup Factory Analytics Engine")
    print("=" * 40)
    
    # Create analytics engine
    engine = AnalyticsEngine()
    
    # Simulate some data
    print("Generating sample data...")
    engine.simulate_data()
    
    # Generate report
    print("\nGenerating analytics report...")
    report = engine.generate_report(format='summary')
    print(report)
    
    # Real-time metrics
    print("\n" + "=" * 40)
    print("Real-time Metrics:")
    metrics = engine.get_real_time_metrics()
    
    perf = metrics['performance']
    print(f"• Total Startups: {perf.get('total_startups', 0)}")
    print(f"• Success Rate: {perf.get('success_rate', 0):.1%}")
    print(f"• Avg Creation Time: {perf.get('avg_completion_time_minutes', 0):.1f} min")
    
    bottlenecks = metrics['bottlenecks']
    if bottlenecks:
        print(f"• Active Bottlenecks: {len(bottlenecks)}")
        for bottleneck in bottlenecks[:2]:
            print(f"  - {bottleneck['description']}")

if __name__ == "__main__":
    main()