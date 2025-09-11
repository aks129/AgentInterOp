"""
Dialog arbiter for autonomous BCS evaluation decisions.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from .guidelines import GuidelinesEvaluator


class DialogArbiter:
    """Arbitrates between agent proposals to determine final outcome."""
    
    def __init__(self, guidelines: Dict[str, Any] = None):
        self.guidelines_evaluator = GuidelinesEvaluator(guidelines)
    
    def determine_outcome(self, turns: List[Any]) -> Dict[str, Any]:
        """
        Analyze dialog turns and determine final outcome.
        
        Args:
            turns: List of DialogTurn objects from autonomous dialog
            
        Returns:
            Final outcome with chosen decision, rationale, and confidence
        """
        if not turns:
            return {
                "chosen": "needs-more-info",
                "reason": "No dialog turns available",
                "confidence": 0.1,
                "method": "default",
                "timestamp": datetime.now().isoformat()
            }
        
        # Extract all proposals from turns
        proposals = self._extract_proposals(turns)
        
        if not proposals:
            return {
                "chosen": "needs-more-info", 
                "reason": "No proposals found in dialog",
                "confidence": 0.2,
                "method": "default",
                "timestamp": datetime.now().isoformat()
            }
        
        # Get the most recent facts from dialog context
        facts = self._extract_facts_from_turns(turns)
        
        # Evaluate against guidelines
        guidelines_result = self._evaluate_against_guidelines(facts)
        
        # Apply arbitration logic
        chosen_outcome = self._arbitrate_proposals(proposals, guidelines_result)
        
        return {
            "chosen": chosen_outcome["decision"],
            "reason": chosen_outcome["rationale"],
            "confidence": chosen_outcome["confidence"],
            "method": chosen_outcome["method"],
            "guidelines_decision": guidelines_result.get("decision"),
            "proposals_considered": len(proposals),
            "timestamp": datetime.now().isoformat(),
            "details": {
                "guidelines_evaluation": guidelines_result,
                "proposals": proposals,
                "arbitration_factors": chosen_outcome.get("factors", {})
            }
        }
    
    def _extract_proposals(self, turns: List[Any]) -> List[Dict[str, Any]]:
        """Extract decision proposals from dialog turns."""
        proposals = []
        
        for turn in turns:
            if not turn.response:
                continue
                
            actions = turn.response.get("actions", [])
            for action in actions:
                if action.get("kind") == "propose_decision":
                    proposal = {
                        "turn": turn.turn_number,
                        "agent": turn.agent_role.value,
                        "decision": action.get("decision"),
                        "rationale": action.get("rationale", ""),
                        "confidence": turn.response.get("confidence", 0.5),
                        "timestamp": turn.timestamp,
                        "source": turn.source
                    }
                    proposals.append(proposal)
        
        return proposals
    
    def _extract_facts_from_turns(self, turns: List[Any]) -> Dict[str, Any]:
        """Extract patient facts from dialog context."""
        # Look for facts in the most recent turns
        for turn in reversed(turns):
            if hasattr(turn, 'message') and isinstance(turn.message, dict):
                facts = turn.message.get("facts")
                if facts:
                    return facts
        
        # Fallback to empty facts
        return {}
    
    def _evaluate_against_guidelines(self, facts: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate facts against clinical guidelines."""
        if not facts:
            return {
                "decision": "needs-more-info",
                "rationale": "No patient facts available for evaluation",
                "confidence": 0.1
            }
        
        return self.guidelines_evaluator.evaluate(facts)
    
    def _arbitrate_proposals(self, proposals: List[Dict[str, Any]], guidelines_result: Dict[str, Any]) -> Dict[str, Any]:
        """Apply arbitration logic to choose best proposal."""
        if not proposals:
            return {
                "decision": "needs-more-info",
                "rationale": "No proposals to arbitrate",
                "confidence": 0.1,
                "method": "no_proposals"
            }
        
        # Single proposal - validate against guidelines
        if len(proposals) == 1:
            proposal = proposals[0]
            return self._validate_single_proposal(proposal, guidelines_result)
        
        # Multiple proposals - apply preference rules
        return self._choose_among_proposals(proposals, guidelines_result)
    
    def _validate_single_proposal(self, proposal: Dict[str, Any], guidelines_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate single proposal against guidelines."""
        proposal_decision = proposal["decision"]
        guidelines_decision = guidelines_result.get("decision")
        
        # If proposal aligns with guidelines, accept it
        if proposal_decision == guidelines_decision:
            return {
                "decision": proposal_decision,
                "rationale": f"Agent proposal aligns with guidelines: {proposal['rationale']}",
                "confidence": min(proposal["confidence"], guidelines_result.get("confidence", 0.5)),
                "method": "guidelines_aligned",
                "factors": {
                    "guidelines_agreement": True,
                    "agent_confidence": proposal["confidence"],
                    "guidelines_confidence": guidelines_result.get("confidence", 0.5)
                }
            }
        
        # If proposal conflicts with guidelines, prefer guidelines for safety
        if guidelines_result.get("confidence", 0) > 0.7:
            return {
                "decision": guidelines_decision,
                "rationale": f"Guidelines override agent proposal for safety: {guidelines_result.get('rationale', '')}",
                "confidence": guidelines_result.get("confidence", 0.5),
                "method": "guidelines_override", 
                "factors": {
                    "guidelines_agreement": False,
                    "override_reason": "high_confidence_guidelines",
                    "proposal_decision": proposal_decision,
                    "guidelines_decision": guidelines_decision
                }
            }
        
        # Low confidence guidelines - prefer conservative approach
        conservative_decision = self._choose_conservative(proposal_decision, guidelines_decision)
        return {
            "decision": conservative_decision,
            "rationale": f"Conservative choice due to guideline uncertainty: {proposal['rationale']}",
            "confidence": 0.6,
            "method": "conservative",
            "factors": {
                "guidelines_agreement": False,
                "conservative_choice": True,
                "proposal_decision": proposal_decision,
                "guidelines_decision": guidelines_decision
            }
        }
    
    def _choose_among_proposals(self, proposals: List[Dict[str, Any]], guidelines_result: Dict[str, Any]) -> Dict[str, Any]:
        """Choose best proposal from multiple options."""
        guidelines_decision = guidelines_result.get("decision")
        
        # Prefer proposals that align with guidelines
        aligned_proposals = [p for p in proposals if p["decision"] == guidelines_decision]
        if aligned_proposals:
            best_aligned = max(aligned_proposals, key=lambda p: p["confidence"])
            return {
                "decision": best_aligned["decision"],
                "rationale": f"Best aligned proposal: {best_aligned['rationale']}",
                "confidence": min(best_aligned["confidence"], guidelines_result.get("confidence", 0.5)),
                "method": "best_aligned",
                "factors": {
                    "total_proposals": len(proposals),
                    "aligned_proposals": len(aligned_proposals),
                    "chosen_agent": best_aligned["agent"],
                    "chosen_confidence": best_aligned["confidence"]
                }
            }
        
        # No aligned proposals - apply preference rules
        return self._apply_preference_rules(proposals, guidelines_result)
    
    def _apply_preference_rules(self, proposals: List[Dict[str, Any]], guidelines_result: Dict[str, Any]) -> Dict[str, Any]:
        """Apply preference rules when no proposals align with guidelines."""
        
        # Rule 1: Prefer higher confidence proposals
        high_confidence = [p for p in proposals if p["confidence"] > 0.7]
        if high_confidence:
            best_confidence = max(high_confidence, key=lambda p: p["confidence"])
            
            # But validate against safety
            if self._is_safe_decision(best_confidence["decision"], guidelines_result):
                return {
                    "decision": best_confidence["decision"],
                    "rationale": f"High confidence proposal: {best_confidence['rationale']}",
                    "confidence": best_confidence["confidence"],
                    "method": "high_confidence",
                    "factors": {
                        "rule_applied": "high_confidence",
                        "chosen_agent": best_confidence["agent"],
                        "safety_validated": True
                    }
                }
        
        # Rule 2: Prefer decisions that lead to patient action (eligible > needs-info > ineligible)
        decision_priority = {"eligible": 3, "needs-more-info": 2, "ineligible": 1}
        
        proposals_by_priority = sorted(proposals, key=lambda p: decision_priority.get(p["decision"], 0), reverse=True)
        best_priority = proposals_by_priority[0]
        
        if self._is_safe_decision(best_priority["decision"], guidelines_result):
            return {
                "decision": best_priority["decision"],
                "rationale": f"Priority-based choice: {best_priority['rationale']}",
                "confidence": best_priority["confidence"] * 0.8,  # Reduce confidence for non-aligned choice
                "method": "priority_rule",
                "factors": {
                    "rule_applied": "decision_priority",
                    "chosen_agent": best_priority["agent"],
                    "safety_validated": True
                }
            }
        
        # Rule 3: Conservative fallback
        return {
            "decision": "needs-more-info",
            "rationale": "Conservative fallback due to conflicting proposals and guideline uncertainty",
            "confidence": 0.5,
            "method": "conservative_fallback",
            "factors": {
                "rule_applied": "conservative_fallback",
                "total_proposals": len(proposals),
                "guidelines_uncertainty": True
            }
        }
    
    def _is_safe_decision(self, decision: str, guidelines_result: Dict[str, Any]) -> bool:
        """Check if a decision is safe given guidelines."""
        guidelines_decision = guidelines_result.get("decision")
        
        # Always safe to request more info
        if decision == "needs-more-info":
            return True
        
        # If guidelines are confident and disagree, not safe
        if (guidelines_result.get("confidence", 0) > 0.8 and 
            decision != guidelines_decision):
            return False
        
        # If proposing eligible but guidelines say ineligible, not safe
        if decision == "eligible" and guidelines_decision == "ineligible":
            return False
        
        return True
    
    def _choose_conservative(self, decision1: str, decision2: str) -> str:
        """Choose more conservative decision between two options."""
        # Priority: needs-more-info > ineligible > eligible
        conservative_order = ["needs-more-info", "ineligible", "eligible"]
        
        for conservative_choice in conservative_order:
            if decision1 == conservative_choice or decision2 == conservative_choice:
                return conservative_choice
        
        return "needs-more-info"  # Ultimate fallback


def arbitrate_test_cases() -> List[Dict[str, Any]]:
    """Test arbiter with various scenarios."""
    arbiter = DialogArbiter()
    
    # Mock turn objects for testing
    class MockTurn:
        def __init__(self, turn_number, agent_role, response, timestamp=None):
            self.turn_number = turn_number
            self.agent_role = type('AgentRole', (), {'value': agent_role})()
            self.response = response
            self.timestamp = timestamp or datetime.now().isoformat()
            self.source = "claude"
            self.message = {}
    
    test_cases = [
        {
            "name": "Aligned_Proposals",
            "turns": [
                MockTurn(1, "applicant", {
                    "actions": [{"kind": "provide_info", "data": {"sex": "female", "birthDate": "1969-08-10", "last_mammogram": "2022-01-01"}}]
                }),
                MockTurn(2, "administrator", {
                    "actions": [{"kind": "propose_decision", "decision": "eligible", "rationale": "Meets criteria"}],
                    "confidence": 0.9
                })
            ]
        },
        {
            "name": "Conflicting_Proposals", 
            "turns": [
                MockTurn(1, "applicant", {
                    "actions": [{"kind": "propose_decision", "decision": "eligible", "rationale": "Patient needs screening"}],
                    "confidence": 0.7
                }),
                MockTurn(2, "administrator", {
                    "actions": [{"kind": "propose_decision", "decision": "needs-more-info", "rationale": "Missing documentation"}],
                    "confidence": 0.8
                })
            ]
        }
    ]
    
    results = []
    for case in test_cases:
        outcome = arbiter.determine_outcome(case["turns"])
        results.append({
            "test_name": case["name"],
            "outcome": outcome,
            "method": outcome["method"],
            "confidence": outcome["confidence"]
        })
    
    return results