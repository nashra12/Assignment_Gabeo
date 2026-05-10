"""
Open-source version of pattern matcher using sentence-transformers (local embeddings).

This version uses:
- sentence-transformers (all-MiniLM-L6-v2) - free, runs locally
- No API keys required
- Same interface as the original pattern matcher
"""
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import asdict

from src.models import (
    Remittance835, ClaimSubmission837, HistoricalPattern, DenialAnalysis
)
from src.config import Config


class PatternMatcherOpenSource:
    """
    Open-source pattern matcher using local embeddings.
    
    Uses sentence-transformers instead of OpenAI API:
    - Model: all-MiniLM-L6-v2 (384 dimensions, very fast)
    - Alternative: all-mpnet-base-v2 (768 dimensions, better quality)
    - Runs completely offline after initial download
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize with local embedding model.
        
        Args:
            model_name: sentence-transformers model name
                - "all-MiniLM-L6-v2" - Fast, 384-dim (recommended)
                - "all-mpnet-base-v2" - Better quality, 768-dim
        """
        self.config = Config()
        
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. Install with:\n"
                "  pip install sentence-transformers"
            )
        
        print(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        print("Model loaded!")
        
        # In-memory storage (same as original)
        self.claim_embeddings: Dict[str, np.ndarray] = {}
        self.claim_metadata: Dict[str, Dict[str, Any]] = {}
        self.paid_claims: Dict[str, Tuple[Remittance835, ClaimSubmission837]] = {}
    
    def index_claim(
        self,
        remittance: Remittance835,
        submission: ClaimSubmission837,
        is_paid: bool = True
    ) -> None:
        """
        Index a claim for future similarity search.
        
        Args:
            remittance: EDI 835 data
            submission: EDI 837 data
            is_paid: Whether this claim was paid (for pattern matching)
        """
        claim_id = remittance.claim_id
        
        # Generate embedding using local model
        claim_text = self._claim_to_text(remittance, submission)
        embedding = self._get_embedding(claim_text)
        
        # Store
        self.claim_embeddings[claim_id] = embedding
        self.claim_metadata[claim_id] = {
            "payer": submission.payer_name,
            "insurance_type": submission.insurance_type,
            "procedures": [line.procedure_code for line in remittance.service_lines],
            "diagnoses": [submission.principal_diagnosis] + submission.additional_diagnoses,
            "amount": remittance.claim_amount,
            "paid_amount": remittance.claim_paid,
            "is_paid": is_paid,
            "specialty": submission.rend_prov_specialty
        }
        
        if is_paid:
            self.paid_claims[claim_id] = (remittance, submission)
    
    def find_similar_paid_claims(
        self,
        denied_remittance: Remittance835,
        denied_submission: ClaimSubmission837,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, float, Remittance835, ClaimSubmission837]]:
        """
        Find historically paid claims similar to a denied claim.
        
        Args:
            denied_remittance: Denied claim 835 data
            denied_submission: Denied claim 837 data
            top_k: Number of similar claims to return
            filters: Optional filters (e.g., same payer, same procedure)
            
        Returns:
            List of (claim_id, similarity_score, remittance, submission) tuples
        """
        # Generate embedding for denied claim
        denied_text = self._claim_to_text(denied_remittance, denied_submission)
        denied_embedding = self._get_embedding(denied_text)
        
        # Compute similarities
        similarities = []
        for claim_id, embedding in self.claim_embeddings.items():
            metadata = self.claim_metadata[claim_id]
            
            # Skip non-paid claims
            if not metadata["is_paid"]:
                continue
            
            # Apply filters
            if filters:
                if "payer" in filters and metadata["payer"] != filters["payer"]:
                    continue
                if "insurance_type" in filters and metadata["insurance_type"] != filters["insurance_type"]:
                    continue
                if "procedure_overlap" in filters:
                    denied_procs = set([line.procedure_code for line in denied_remittance.service_lines])
                    if not denied_procs.intersection(set(metadata["procedures"])):
                        continue
            
            # Compute cosine similarity
            similarity = self._cosine_similarity(denied_embedding, embedding)
            
            # Apply threshold
            if similarity >= self.config.SIMILARITY_THRESHOLD:
                similarities.append((claim_id, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Return top_k with full claim data
        results = []
        for claim_id, score in similarities[:top_k]:
            if claim_id in self.paid_claims:
                remittance, submission = self.paid_claims[claim_id]
                results.append((claim_id, score, remittance, submission))
        
        return results
    
    def compute_denial_patterns(
        self,
        payer: Optional[str] = None,
        procedure_code: Optional[str] = None
    ) -> HistoricalPattern:
        """
        Compute aggregate denial patterns from indexed claims.
        
        Args:
            payer: Filter by specific payer
            procedure_code: Filter by specific procedure
            
        Returns:
            HistoricalPattern with aggregate statistics
        """
        # Filter claims
        relevant_claims = []
        for claim_id, metadata in self.claim_metadata.items():
            if payer and metadata["payer"] != payer:
                continue
            if procedure_code and procedure_code not in metadata["procedures"]:
                continue
            relevant_claims.append((claim_id, metadata))
        
        if not relevant_claims:
            return None
        
        # Compute statistics
        total_claims = len(relevant_claims)
        denied_claims = sum(1 for _, meta in relevant_claims if meta["paid_amount"] == 0)
        denial_rate = denied_claims / total_claims if total_claims > 0 else 0.0
        
        paid_claims_only = [meta for _, meta in relevant_claims if meta["paid_amount"] > 0]
        avg_paid = (
            sum(meta["paid_amount"] for meta in paid_claims_only) / len(paid_claims_only)
            if paid_claims_only else 0.0
        )
        
        # Collect common procedures and diagnoses
        all_procedures = []
        all_diagnoses = []
        for _, meta in relevant_claims:
            all_procedures.extend(meta["procedures"])
            all_diagnoses.extend(meta["diagnoses"])
        
        common_procedures = list(set(all_procedures))[:10]  # Top 10
        common_diagnoses = list(set([d for d in all_diagnoses if d]))[:10]
        
        return HistoricalPattern(
            pattern_id=f"{payer or 'all'}_{procedure_code or 'all'}",
            payer_name=payer or "All Payers",
            procedure_codes=common_procedures,
            diagnosis_codes=common_diagnoses,
            denial_rate=denial_rate,
            average_paid_amount=avg_paid,
            sample_size=total_claims,
            common_denial_reasons=[],
            success_rate_on_appeal=None
        )
    
    def _claim_to_text(
        self,
        remittance: Remittance835,
        submission: ClaimSubmission837
    ) -> str:
        """Convert claim data to text for embedding."""
        # Same as original - focus on key fields
        parts = []
        
        # Payer and insurance type
        parts.append(f"Payer: {submission.payer_name or 'Unknown'}")
        parts.append(f"Insurance: {submission.insurance_type}")
        
        # Procedures
        procedures = [line.procedure_code for line in remittance.service_lines]
        parts.append(f"Procedures: {', '.join(procedures)}")
        
        # Modifiers
        modifiers = []
        for line in remittance.service_lines:
            modifiers.extend([m for m in line.modifiers if m])
        if modifiers:
            parts.append(f"Modifiers: {', '.join(modifiers)}")
        
        # Diagnoses
        diagnoses = [submission.principal_diagnosis] + submission.additional_diagnoses
        diagnoses = [d for d in diagnoses if d]
        if diagnoses:
            parts.append(f"Diagnoses: {', '.join(diagnoses[:5])}")  # Top 5
        
        # Provider specialty
        if submission.rend_prov_specialty:
            parts.append(f"Specialty: {submission.rend_prov_specialty}")
        
        # Place of service
        if submission.place_of_service:
            parts.append(f"Place of Service: {submission.place_of_service}")
        
        # Amount bucket
        amount = remittance.claim_amount
        if amount < 1000:
            bucket = "low"
        elif amount < 5000:
            bucket = "medium"
        elif amount < 20000:
            bucket = "high"
        else:
            bucket = "very_high"
        parts.append(f"Amount tier: {bucket}")
        
        return " | ".join(parts)
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding vector using local model."""
        try:
            # sentence-transformers returns numpy array directly
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            raise RuntimeError(f"Embedding generation failed: {str(e)}")
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def get_pattern_context(
        self,
        remittance: Remittance835,
        submission: ClaimSubmission837
    ) -> str:
        """
        Get historical pattern context for a claim to include in LLM prompt.
        
        Returns formatted string with similar paid claims info.
        """
        similar_claims = self.find_similar_paid_claims(
            remittance, submission, top_k=3
        )
        
        if not similar_claims:
            return "No similar paid claims found in historical data."
        
        lines = ["Similar Historically Paid Claims:"]
        for idx, (claim_id, score, rem, sub) in enumerate(similar_claims, 1):
            lines.append(f"\n{idx}. Claim {claim_id} (Similarity: {score:.2f})")
            lines.append(f"   Payer: {sub.payer_name}")
            lines.append(f"   Procedures: {', '.join([l.procedure_code for l in rem.service_lines])}")
            lines.append(f"   Billed: ${rem.claim_amount:,.2f}, Paid: ${rem.claim_paid:,.2f}")
            lines.append(f"   Diagnoses: {sub.principal_diagnosis}")
        
        # Get aggregate pattern
        pattern = self.compute_denial_patterns(
            payer=submission.payer_name
        )
        
        if pattern:
            lines.append(f"\nPayer Pattern ({pattern.payer_name}):")
            lines.append(f"  Sample size: {pattern.sample_size} claims")
            lines.append(f"  Denial rate: {pattern.denial_rate:.1%}")
            lines.append(f"  Avg paid amount: ${pattern.average_paid_amount:,.2f}")
        
        return "\n".join(lines)
