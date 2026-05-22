# core/metrics.py
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any
import json
import logging
from config import METRICS_PATH

logger = logging.getLogger(__name__)

@dataclass
class PipelineMetrics:
    timestamp: str
    claim_extraction_time: float
    retrieval_time: float
    llm_time: float
    total_time: float
    verdict: str
    confidence: float
    num_evidence_retrieved: int
    cache_hit: bool
    input_length: int

class MetricsCollector:
    """Collect and analyze pipeline performance metrics"""
    
    def __init__(self):
        self.metrics: List[PipelineMetrics] = []
        self.load_from_disk()
    
    def log_metric(self, metric: PipelineMetrics):
        """Log a metric entry"""
        self.metrics.append(metric)
        
        # Write to disk (append mode)
        try:
            METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(METRICS_PATH, 'a') as f:
                f.write(json.dumps(asdict(metric)) + '\n')
        except Exception as e:
            logger.error(f"Failed to write metric: {e}")
    
    def load_from_disk(self):
        """Load metrics from disk"""
        try:
            if METRICS_PATH.exists():
                with open(METRICS_PATH, 'r') as f:
                    for line in f:
                        data = json.loads(line.strip())
                        self.metrics.append(PipelineMetrics(**data))
                logger.info(f"Loaded {len(self.metrics)} metrics from disk")
        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        if not self.metrics:
            return {
                'total_queries': 0,
                'message': 'No metrics collected yet'
            }
        
        recent = self.metrics[-100:]  # Last 100 queries
        
        return {
            'total_queries': len(self.metrics),
            'recent_queries': len(recent),
            'avg_total_time': sum(m.total_time for m in recent) / len(recent),
            'avg_confidence': sum(m.confidence for m in recent) / len(recent),
            'cache_hit_rate': sum(1 for m in recent if m.cache_hit) / len(recent),
            'verdict_distribution': {
                'True': sum(1 for m in recent if m.verdict == 'True'),
                'False': sum(1 for m in recent if m.verdict == 'False'),
                'Unverifiable': sum(1 for m in recent if m.verdict == 'Unverifiable'),
            },
            'avg_evidence_count': sum(m.num_evidence_retrieved for m in recent) / len(recent)
        }

metrics_collector = MetricsCollector()