import numpy as np
from typing import List, Dict, Any, Tuple
from collections import defaultdict, Counter
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

from src.models import (
    DenialAnalysis, Remittance835, ClaimSubmission837, DenialCluster
)
from src.config import Config


class DenialClusterer:
    """
    Groups denied claims into meaningful clusters for batch processing.
    
    Clustering dimensions:
    - Denial reason (CARC codes)
    - Payer
    - Procedure type
    - Financial amount
    - Recoverability score
    """
    
    def __init__(self):
        """Initialize clusterer."""
        self.config = Config()
    
    def cluster_denials(
        self,
        denials: List[Tuple[DenialAnalysis, Remittance835, ClaimSubmission837]]
    ) -> List[DenialCluster]:
        """
        Cluster denied claims into actionable groups.
        
        Args:
            denials: List of (analysis, remittance, submission) tuples
            
        Returns:
            List of DenialCluster objects
        """
        if len(denials) < self.config.MIN_CLUSTER_SIZE:
            # Not enough data for clustering
            return self._create_single_cluster(denials)
        
        # Create feature matrix
        features, feature_names = self._extract_features(denials)
        
        # Normalize features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # Perform clustering (DBSCAN for variable cluster count)
        clusterer = DBSCAN(eps=0.5, min_samples=self.config.MIN_CLUSTER_SIZE)
        cluster_labels = clusterer.fit_predict(features_scaled)
        
        # Group denials by cluster
        clusters_dict = defaultdict(list)
        for idx, label in enumerate(cluster_labels):
            clusters_dict[label].append(denials[idx])
        
        # Create DenialCluster objects
        clusters = []
        for cluster_id, cluster_denials in clusters_dict.items():
            if cluster_id == -1:  # Noise in DBSCAN
                label = "Miscellaneous"
            else:
                label = self._generate_cluster_label(cluster_denials)
            
            cluster = self._build_cluster(
                cluster_id=f"CLUSTER_{cluster_id}",
                label=label,
                denials=cluster_denials
            )
            clusters.append(cluster)
        
        # Sort by expected recovery amount (descending)
        clusters.sort(key=lambda c: c.expected_recovery_amount, reverse=True)
        
        return clusters
    
    def _extract_features(
        self,
        denials: List[Tuple[DenialAnalysis, Remittance835, ClaimSubmission837]]
    ) -> Tuple[np.ndarray, List[str]]:
        """Extract numerical features for clustering."""
        features = []
        feature_names = [
            "amount", "confidence", "recoverability_score",
            "payer_hash", "primary_carc_hash", "category_hash"
        ]
        
        for analysis, remittance, submission in denials:
            feature_vec = []
            
            # Financial amount (log scale)
            feature_vec.append(np.log1p(analysis.financial_impact))
            
            # Confidence score
            feature_vec.append(analysis.confidence_score)
            
            # Recoverability (numerical encoding)
            recov_map = {"recoverable": 1.0, "needs_review": 0.5, "not_recoverable": 0.0}
            feature_vec.append(recov_map.get(analysis.recoverability, 0.5))
            
            # Payer (hash to number)
            payer = submission.payer_name or "Unknown"
            feature_vec.append(hash(payer) % 1000 / 1000.0)
            
            # Primary CARC code (hash)
            primary_carc = analysis.carc_codes[0] if analysis.carc_codes else "0"
            feature_vec.append(hash(primary_carc) % 1000 / 1000.0)
            
            # Category (hash)
            feature_vec.append(hash(analysis.denial_category) % 1000 / 1000.0)
            
            features.append(feature_vec)
        
        return np.array(features), feature_names
    
    def _generate_cluster_label(
        self,
        cluster_denials: List[Tuple[DenialAnalysis, Remittance835, ClaimSubmission837]]
    ) -> str:
        """Generate human-readable label for a cluster."""
        # Count common attributes
        payers = [sub.payer_name for _, _, sub in cluster_denials]
        carcs = []
        categories = []
        
        for analysis, _, _ in cluster_denials:
            carcs.extend(analysis.carc_codes)
            categories.append(analysis.denial_category)
        
        # Most common payer
        payer_counts = Counter([p for p in payers if p])
        common_payer = payer_counts.most_common(1)[0][0] if payer_counts else "Multiple"
        
        # Most common CARC
        carc_counts = Counter(carcs)
        common_carc = carc_counts.most_common(1)[0][0] if carc_counts else "Various"
        
        # Most common category
        category_counts = Counter(categories)
        common_category = category_counts.most_common(1)[0][0] if category_counts else "mixed"
        
        # Format label
        category_labels = {
            "timely_filing": "Late Filing",
            "missing_information": "Missing Info",
            "medical_necessity": "Med Necessity",
            "duplicate": "Duplicates",
            "coding_error": "Coding Issues",
            "authorization": "Prior Auth",
            "non_covered": "Non-Covered",
        }
        
        category_text = category_labels.get(common_category, common_category)
        
        return f"{common_payer} - {category_text} (CARC {common_carc})"
    
    def _build_cluster(
        self,
        cluster_id: str,
        label: str,
        denials: List[Tuple[DenialAnalysis, Remittance835, ClaimSubmission837]]
    ) -> DenialCluster:
        """Build DenialCluster object with aggregated statistics."""
        # Aggregate financial data
        total_amount = sum(analysis.financial_impact for analysis, _, _ in denials)
        
        # Aggregate recoverability
        recov_scores = []
        for analysis, _, _ in denials:
            if analysis.recoverability == "recoverable":
                recov_scores.append(0.8)
            elif analysis.recoverability == "needs_review":
                recov_scores.append(0.5)
            else:
                recov_scores.append(0.2)
        
        avg_recoverability = sum(recov_scores) / len(recov_scores) if recov_scores else 0.0
        
        # Expected recovery
        expected_recovery = total_amount * avg_recoverability
        
        # Common denial reasons
        all_carcs = []
        for analysis, _, _ in denials:
            all_carcs.extend(analysis.carc_codes)
        
        carc_counts = Counter(all_carcs)
        primary_reasons = [f"CARC {code}" for code, _ in carc_counts.most_common(3)]
        
        # Payers
        payers = list(set([sub.payer_name for _, _, sub in denials if sub.payer_name]))
        
        # Recommended action
        if avg_recoverability > 0.6:
            action = "High-priority batch appeal recommended"
            priority = "high"
        elif avg_recoverability > 0.3:
            action = "Review and selectively appeal"
            priority = "medium"
        else:
            action = "Low recovery potential - consider write-off"
            priority = "low"
        
        return DenialCluster(
            cluster_id=cluster_id,
            cluster_label=label,
            claim_count=len(denials),
            total_amount=total_amount,
            avg_recoverability_score=avg_recoverability,
            primary_denial_reasons=primary_reasons,
            payers=payers,
            recommended_batch_action=action,
            expected_recovery_amount=expected_recovery,
            expected_recovery_rate=avg_recoverability
        )
    
    def _create_single_cluster(
        self,
        denials: List[Tuple[DenialAnalysis, Remittance835, ClaimSubmission837]]
    ) -> List[DenialCluster]:
        """Create a single cluster when data is too small."""
        return [self._build_cluster(
            cluster_id="CLUSTER_0",
            label="All Denials",
            denials=denials
        )]
    
    def prioritize_clusters(
        self, clusters: List[DenialCluster]
    ) -> List[DenialCluster]:
        """
        Sort clusters by priority based on multiple factors.
        
        Priority score = (expected_recovery * 0.6) + (claim_count * 0.2) + (recoverability * 0.2)
        """
        def priority_score(cluster: DenialCluster) -> float:
            # Normalize factors
            recovery_norm = min(cluster.expected_recovery_amount / 10000, 10.0)
            count_norm = min(cluster.claim_count / 10, 10.0)
            recov_norm = cluster.avg_recoverability_score * 10
            
            return (recovery_norm * 0.6) + (count_norm * 0.2) + (recov_norm * 0.2)
        
        return sorted(clusters, key=priority_score, reverse=True)
    
    def generate_batch_report(
        self, clusters: List[DenialCluster]
    ) -> str:
        """Generate executive summary report for billing teams."""
        lines = []
        lines.append("=" * 70)
        lines.append("DENIAL BATCH ANALYSIS REPORT")
        lines.append("=" * 70)
        lines.append("")
        
        # Overall statistics
        total_claims = sum(c.claim_count for c in clusters)
        total_amount = sum(c.total_amount for c in clusters)
        total_recovery = sum(c.expected_recovery_amount for c in clusters)
        
        lines.append("EXECUTIVE SUMMARY:")
        lines.append(f"  Total Denied Claims: {total_claims}")
        lines.append(f"  Total Denied Amount: ${total_amount:,.2f}")
        if total_amount > 0:
            lines.append(f"  Expected Recoverable: ${total_recovery:,.2f} ({total_recovery/total_amount:.1%})")
        else:
            lines.append(f"  Expected Recoverable: ${total_recovery:,.2f} (0.0%)")
        lines.append("")
        
        # Cluster details
        lines.append("CLUSTERS BY PRIORITY:")
        lines.append("")
        
        for idx, cluster in enumerate(clusters, 1):
            # Determine priority based on total amount
            if cluster.total_amount > 10000:
                priority = "HIGH"
            elif cluster.total_amount > 2000:
                priority = "MEDIUM"
            else:
                priority = "LOW"
            
            lines.append(f"{idx}. {cluster.cluster_label}")

            lines.append(f"   Claims: {cluster.claim_count}")
            lines.append(f"   Amount: ${cluster.total_amount:,.2f}")
            lines.append(f"   Expected Recovery: ${cluster.expected_recovery_amount:,.2f} ({cluster.expected_recovery_rate:.1%})")
            lines.append(f"   Priority: {priority}")
            lines.append(f"   Payers: {', '.join(cluster.payers[:3])}")
            lines.append(f"   Common Reasons: {', '.join(cluster.primary_denial_reasons)}")
            lines.append(f"   Action: {cluster.recommended_batch_action}")
            lines.append("")
        
        return "\n".join(lines)