"""
Open-source pipeline using local models (no API keys required).

This version uses:
- Ollama for LLM (qwen2.5:7b or llama3.1:8b)
- sentence-transformers for embeddings (all-MiniLM-L6-v2)
- 100% free and runs locally
"""
import json
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path

from src.models import Remittance835, ClaimSubmission837, DenialAnalysis
from analyzer_opensource import ClaimAnalyzerOpenSource
from pattern_matcher_opensource import PatternMatcherOpenSource
from src.clusterer import DenialClusterer  # Same as original
from src.synthetic_generator import SyntheticClaimGenerator  # Same as original


class DenialAnalysisPipelineOpenSource:
    """
    Open-source version of the analysis pipeline.
    
    Requirements:
    - Ollama installed (curl -fsSL https://ollama.com/install.sh | sh)
    - Model pulled (ollama pull qwen2.5:7b)
    - sentence-transformers installed (pip install sentence-transformers)
    
    Total cost: $0 (all local processing)
    """
    
    def __init__(
        self,
        llm_model: str = "qwen2.5:7b",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize pipeline with local models.
        
        Args:
            llm_model: Ollama model name ("qwen2.5:7b", "llama3.1:8b", etc.)
            embedding_model: sentence-transformers model name
        """
        print(f"Initializing open-source pipeline...")
        print(f"  LLM: {llm_model} (via Ollama)")
        print(f"  Embeddings: {embedding_model} (via sentence-transformers)")
        
        self.analyzer = ClaimAnalyzerOpenSource(model_name=llm_model)
        self.pattern_matcher = PatternMatcherOpenSource(model_name=embedding_model)
        self.clusterer = DenialClusterer()
        
        print("Pipeline ready!")
    
    def process_claims(
        self,
        claims: List[Tuple[Remittance835, ClaimSubmission837, bool]]
    ) -> Dict[str, Any]:
        """
        Process a batch of claims through the full pipeline.
        
        Args:
            claims: List of (remittance, submission, is_denied) tuples
            
        Returns:
            Dictionary with analysis results, clusters, and reports
        """
        print(f"\n{'='*70}")
        print(f"Processing {len(claims)} claims...")
        print(f"{'='*70}")
        
        # Separate paid and denied claims
        paid_claims = [(r, s) for r, s, denied in claims if not denied]
        denied_claims = [(r, s) for r, s, denied in claims if denied]
        
        print(f"  - {len(paid_claims)} paid claims")
        print(f"  - {len(denied_claims)} denied claims")
        
        # Index paid claims for pattern matching
        print(f"\n{'─'*70}")
        print("Indexing historical paid claims...")
        print(f"{'─'*70}")
        for idx, (remittance, submission) in enumerate(paid_claims, 1):
            print(f"  [{idx}/{len(paid_claims)}] Indexing {remittance.claim_id}...")
            self.pattern_matcher.index_claim(remittance, submission, is_paid=True)
        print(f"✓ Indexed {len(paid_claims)} claims")
        
        # Analyze each denied claim
        print(f"\n{'─'*70}")
        print("Analyzing denied claims...")
        print(f"{'─'*70}")
        analyses = []
        for idx, (remittance, submission) in enumerate(denied_claims, 1):
            print(f"\n[{idx}/{len(denied_claims)}] Analyzing {remittance.claim_id}...")
            
            # Get historical context
            print("  • Finding similar historical claims...")
            historical_context = self.pattern_matcher.get_pattern_context(
                remittance, submission
            )
            
            # Perform analysis
            try:
                print("  • Running LLM analysis (this may take 30-60 seconds)...")
                analysis = self.analyzer.analyze_denial(
                    remittance, submission, historical_context
                )
                analyses.append((analysis, remittance, submission))
                print(f"  ✓ Result: {analysis.recoverability} (confidence: {analysis.confidence_score:.2f})")
            except Exception as e:
                print(f"  ✗ ERROR: {str(e)}")
                continue
        
        # Cluster denials
        print(f"\n{'─'*70}")
        print("Clustering denials for batch processing...")
        print(f"{'─'*70}")
        clusters = self.clusterer.cluster_denials(analyses)
        print(f"✓ Created {len(clusters)} clusters")
        
        # Generate reports
        print(f"\n{'─'*70}")
        print("Generating reports...")
        print(f"{'─'*70}")
        batch_report = self.clusterer.generate_batch_report(clusters)
        
        # Compile results
        results = {
            "summary": {
                "total_claims": len(claims),
                "paid_claims": len(paid_claims),
                "denied_claims": len(denied_claims),
                "analyzed_claims": len(analyses),
                "clusters": len(clusters)
            },
            "analyses": [
                {
                    "claim_id": analysis.claim_id,
                    "root_cause": analysis.root_cause,
                    "recoverability": analysis.recoverability,
                    "confidence": analysis.confidence_score,
                    "financial_impact": analysis.financial_impact,
                    "recommended_action": analysis.recommended_action,
                    "appeal_priority": analysis.appeal_priority,
                    "evidence": analysis.evidence
                }
                for analysis, _, _ in analyses
            ],
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "label": c.cluster_label,
                    "claim_count": c.claim_count,
                    "total_amount": c.total_amount,
                    "expected_recovery": c.expected_recovery_amount,
                    "recovery_rate": c.expected_recovery_rate,
                    "recommended_action": c.recommended_batch_action
                }
                for c in clusters
            ],
            "batch_report": batch_report
        }
        
        return results
    
    def save_results(self, results: Dict[str, Any], output_dir: str) -> None:
        """Save analysis results to files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save JSON results
        with open(output_path / "analysis_results.json", 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Save batch report
        with open(output_path / "batch_report.txt", 'w') as f:
            f.write(results["batch_report"])
        
        # Save individual analyses
        with open(output_path / "detailed_analyses.json", 'w') as f:
            json.dump(results["analyses"], f, indent=2, default=str)
        
        print(f"\n✓ Results saved to {output_dir}/")


def main():
    """Main entry point for open-source demo."""
    
    print("=" * 70)
    print("CLAIM DENIAL ANALYSIS SYSTEM - OPEN SOURCE VERSION")
    print("=" * 70)
    print("\nNo API keys required! Uses:")
    print("  • Ollama (local LLM)")
    print("  • sentence-transformers (local embeddings)")
    print("  • 100% free and runs offline\n")
    
    # Generate synthetic dataset
    print("1. Generating synthetic test dataset...")
    generator = SyntheticClaimGenerator()
    claims = generator.generate_dataset(num_claims=30, denial_rate=0.4)
    print(f"   ✓ Generated {len(claims)} claims")
    
    # Save dataset
    generator.save_dataset(claims, "data/synthetic_claims.json")
    print("   ✓ Saved to data/synthetic_claims.json")
    
    # Initialize pipeline
    print("\n2. Initializing analysis pipeline...")
    pipeline = DenialAnalysisPipelineOpenSource(
        llm_model="qwen2.5:7b",  # or "llama3.1:8b"
        embedding_model="all-MiniLM-L6-v2"
    )
    
    # Process claims
    print("\n3. Processing claims through pipeline...")
    results = pipeline.process_claims(claims)
    
    # Save results
    print("\n4. Saving results...")
    pipeline.save_results(results, "outputs")
    
    # Print summary
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"\nTotal Denied Amount: ${sum(a['financial_impact'] for a in results['analyses']):,.2f}")
    print(f"Expected Recovery: ${sum(c['expected_recovery'] for c in results['clusters']):,.2f}")
    print(f"\nRecoverability Breakdown:")
    
    recov_counts = {}
    for analysis in results['analyses']:
        recov = analysis['recoverability']
        recov_counts[recov] = recov_counts.get(recov, 0) + 1
    
    for recov, count in recov_counts.items():
        print(f"  {recov}: {count} claims")
    
    print(f"\nClusters created: {len(results['clusters'])}")
    print("\nSee outputs/ directory for detailed reports.")
    print("\n💰 Total Cost: $0 (all local processing!)")


if __name__ == "__main__":
    main()
