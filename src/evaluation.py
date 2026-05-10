from typing import List, Dict, Any, Tuple
from collections import Counter
import json

from src.models import DenialAnalysis, Remittance835, ClaimSubmission837


class EvaluationMetrics:
    """
    Evaluation metrics for denial analysis quality.
    
    Metrics:
    1. Root Cause Accuracy - Does the system identify correct denial reasons?
    2. Recoverability Precision - Are "recoverable" predictions accurate?
    3. Confidence Calibration - Are confidence scores well-calibrated?
    4. Evidence Quality - Are evidence citations relevant and accurate?
    5. Clustering Quality - Are clusters meaningful and actionable?
    """
    
    def __init__(self):
        """Initialize evaluator."""
        self.results = {
            "root_cause_accuracy": [],
            "recoverability_precision": [],
            "confidence_calibration": [],
            "evidence_quality": [],
            "clustering_metrics": {}
        }
    
    def evaluate_analysis(
        self,
        analysis: DenialAnalysis,
        ground_truth: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Evaluate a single analysis against ground truth.
        
        Args:
            analysis: System's denial analysis
            ground_truth: Ground truth labels (for synthetic/labeled data)
            
        Returns:
            Dictionary of metric scores
        """
        scores = {}
        
        # Root cause accuracy
        if "expected_category" in ground_truth:
            scores["root_cause_match"] = float(
                analysis.denial_category == ground_truth["expected_category"]
            )
        
        # Recoverability accuracy
        if "expected_recoverability" in ground_truth:
            scores["recoverability_match"] = float(
                analysis.recoverability == ground_truth["expected_recoverability"]
            )
        
        # CARC code detection
        if "expected_carc" in ground_truth:
            detected_carcs = set(analysis.carc_codes)
            expected_carcs = set(ground_truth["expected_carc"])
            
            if expected_carcs:
                precision = len(detected_carcs & expected_carcs) / len(detected_carcs) if detected_carcs else 0
                recall = len(detected_carcs & expected_carcs) / len(expected_carcs)
                scores["carc_precision"] = precision
                scores["carc_recall"] = recall
                scores["carc_f1"] = (
                    2 * precision * recall / (precision + recall)
                    if (precision + recall) > 0 else 0
                )
        
        # Confidence score (should be higher for correct predictions)
        scores["confidence"] = analysis.confidence_score
        
        # Evidence count (should have multiple pieces)
        scores["evidence_count"] = len(analysis.evidence)
        
        return scores
    
    def evaluate_batch(
        self,
        analyses: List[Tuple[DenialAnalysis, Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """
        Evaluate a batch of analyses.
        
        Args:
            analyses: List of (analysis, ground_truth) pairs
            
        Returns:
            Aggregate metrics across the batch
        """
        all_scores = []
        for analysis, ground_truth in analyses:
            scores = self.evaluate_analysis(analysis, ground_truth)
            all_scores.append(scores)
        
        # Aggregate metrics
        metrics = {}
        
        if all_scores:
            # Average each metric
            metric_keys = set()
            for scores in all_scores:
                metric_keys.update(scores.keys())
            
            for key in metric_keys:
                values = [s[key] for s in all_scores if key in s]
                if values:
                    metrics[f"avg_{key}"] = sum(values) / len(values)
                    metrics[f"min_{key}"] = min(values)
                    metrics[f"max_{key}"] = max(values)
        
        return metrics
    
    def evaluate_recoverability_calibration(
        self,
        analyses: List[DenialAnalysis],
        actual_recoveries: List[bool]
    ) -> Dict[str, float]:
        """
        Evaluate how well recoverability predictions align with outcomes.
        
        This would use real appeal outcomes in production.
        """
        if len(analyses) != len(actual_recoveries):
            raise ValueError("Mismatched lengths")
        
        # Group by predicted recoverability
        recoverable_pred = [
            actual_recoveries[i] 
            for i, a in enumerate(analyses)
            if a.recoverability == "recoverable"
        ]
        
        not_recoverable_pred = [
            actual_recoveries[i]
            for i, a in enumerate(analyses)
            if a.recoverability == "not_recoverable"
        ]
        
        needs_review_pred = [
            actual_recoveries[i]
            for i, a in enumerate(analyses)
            if a.recoverability == "needs_review"
        ]
        
        # Calculate success rates
        metrics = {}
        
        if recoverable_pred:
            metrics["recoverable_success_rate"] = sum(recoverable_pred) / len(recoverable_pred)
            metrics["recoverable_count"] = len(recoverable_pred)
        
        if not_recoverable_pred:
            metrics["not_recoverable_success_rate"] = sum(not_recoverable_pred) / len(not_recoverable_pred)
            metrics["not_recoverable_count"] = len(not_recoverable_pred)
        
        if needs_review_pred:
            metrics["needs_review_success_rate"] = sum(needs_review_pred) / len(needs_review_pred)
            metrics["needs_review_count"] = len(needs_review_pred)
        
        return metrics
    
    def evaluate_clustering_quality(
        self,
        clusters: List[Any],  # DenialCluster objects
        analyses: List[DenialAnalysis]
    ) -> Dict[str, float]:
        """
        Evaluate clustering quality.
        
        Metrics:
        - Cluster coherence (within-cluster similarity)
        - Cluster separation (between-cluster distinctness)
        - Size distribution (are clusters balanced?)
        - Financial prioritization (high-value clusters ranked high?)
        """
        metrics = {}
        
        # Size distribution
        sizes = [c.claim_count for c in clusters]
        metrics["avg_cluster_size"] = sum(sizes) / len(sizes) if sizes else 0
        metrics["min_cluster_size"] = min(sizes) if sizes else 0
        metrics["max_cluster_size"] = max(sizes) if sizes else 0
        
        # Financial metrics
        amounts = [c.total_amount for c in clusters]
        recoveries = [c.expected_recovery_amount for c in clusters]
        
        metrics["total_at_stake"] = sum(amounts)
        metrics["total_expected_recovery"] = sum(recoveries)
        metrics["recovery_rate"] = (
            sum(recoveries) / sum(amounts) if sum(amounts) > 0 else 0
        )
        
        # Priority distribution
        priorities = [c.appeal_priority if hasattr(c, 'appeal_priority') else 'medium' 
                     for c in clusters]
        priority_counts = Counter(priorities)
        
        metrics["high_priority_clusters"] = priority_counts.get("high", 0)
        metrics["medium_priority_clusters"] = priority_counts.get("medium", 0)
        metrics["low_priority_clusters"] = priority_counts.get("low", 0)
        
        return metrics
    
    def generate_evaluation_report(
        self,
        batch_metrics: Dict[str, Any],
        clustering_metrics: Dict[str, float]
    ) -> str:
        """Generate human-readable evaluation report."""
        lines = []
        lines.append("=" * 70)
        lines.append("SYSTEM EVALUATION REPORT")
        lines.append("=" * 70)
        lines.append("")
        
        lines.append("ANALYSIS QUALITY METRICS:")
        lines.append("-" * 70)
        
        if batch_metrics:
            for key, value in sorted(batch_metrics.items()):
                if isinstance(value, float):
                    lines.append(f"  {key}: {value:.3f}")
                else:
                    lines.append(f"  {key}: {value}")
        
        lines.append("")
        lines.append("CLUSTERING METRICS:")
        lines.append("-" * 70)
        
        if clustering_metrics:
            for key, value in sorted(clustering_metrics.items()):
                if isinstance(value, float):
                    if "rate" in key or "recovery" in key:
                        lines.append(f"  {key}: {value:.1%}")
                    elif "amount" in key or "stake" in key:
                        lines.append(f"  {key}: ${value:,.2f}")
                    else:
                        lines.append(f"  {key}: {value:.2f}")
                else:
                    lines.append(f"  {key}: {value}")
        
        lines.append("")
        lines.append("=" * 70)
        
        return "\n".join(lines)


def run_evaluation(results_path: str, output_path: str) -> None:
    """
    Run evaluation on pipeline results.
    
    Args:
        results_path: Path to analysis_results.json
        output_path: Where to save evaluation report
    """
    # Load results
    with open(results_path, 'r') as f:
        results = json.load(f)
    
    evaluator = EvaluationMetrics()
    
    # For synthetic data, we can create ground truth based on CARC codes
    # In production, this would come from actual appeal outcomes
    
    analyses_data = results["analyses"]
    clusters_data = results["clusters"]
    
    # Simple heuristic evaluation for demo
    # (In production, use actual appeal outcomes or expert labels)
    
    # Clustering evaluation
    clustering_metrics = {
        "num_clusters": len(clusters_data),
        "total_claims": sum(c["claim_count"] for c in clusters_data),
        "total_at_stake": sum(c["total_amount"] for c in clusters_data),
        "expected_recovery": sum(c["expected_recovery"] for c in clusters_data),
        "avg_recovery_rate": (
            sum(c["expected_recovery"] for c in clusters_data) /
            sum(c["total_amount"] for c in clusters_data)
            if sum(c["total_amount"] for c in clusters_data) > 0 else 0
        )
    }
    
    # Confidence distribution
    confidences = [a["confidence"] for a in analyses_data]
    batch_metrics = {
        "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
        "min_confidence": min(confidences) if confidences else 0,
        "max_confidence": max(confidences) if confidences else 0,
        "total_analyzed": len(analyses_data)
    }
    
    # Recoverability distribution
    recov_counts = Counter(a["recoverability"] for a in analyses_data)
    batch_metrics["recoverable_pct"] = recov_counts.get("recoverable", 0) / len(analyses_data) if analyses_data else 0
    batch_metrics["not_recoverable_pct"] = recov_counts.get("not_recoverable", 0) / len(analyses_data) if analyses_data else 0
    batch_metrics["needs_review_pct"] = recov_counts.get("needs_review", 0) / len(analyses_data) if analyses_data else 0
    
    # Generate report
    report = evaluator.generate_evaluation_report(
        batch_metrics, clustering_metrics
    )
    
    # Save report
    with open(output_path, 'w') as f:
        f.write(report)
    
    print(f"Evaluation report saved to {output_path}")
    print("\n" + report)


if __name__ == "__main__":
    run_evaluation(
        "outputs/analysis_results.json",
        "outputs/evaluation_report.txt"
    )
