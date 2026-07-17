from typing import List, Dict, Any, Tuple
from collections import defaultdict

def group_runs_by_scan_group(runs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Groups a list of run dictionaries by scan_group_id.
    If scan_group_id is None, falls back to using the run's id as its group.
    """
    groups = defaultdict(list)
    for run in runs:
        group_id = run.get("scan_group_id") or run.get("id")
        groups[str(group_id)].append(run)
    return groups

def compute_consensus(runs_in_group: List[Dict[str, Any]], mentioned_run_ids: set) -> float:
    """
    Given a list of runs belonging to the same scan_group (or legacy single run),
    and a set of run_ids where the target brand was mentioned,
    returns the fractional mention rate (0.0 to 1.0) based ONLY on successful passes.
    
    If all passes failed (e.g. status='error'), returns 0.0.
    """
    # Filter only successful runs
    successful_runs = [r for r in runs_in_group if r.get("status") == "complete"]
    
    if not successful_runs:
        return 0.0
        
    mentions = sum(1 for r in successful_runs if r.get("id") in mentioned_run_ids)
    return float(mentions) / len(successful_runs)

def compute_group_metrics(runs: List[Dict[str, Any]], mentioned_run_ids: set) -> Tuple[float, int, int]:
    """
    Given a raw list of runs and a set of mentioned run_ids,
    groups the runs by scan_group_id and calculates the global metrics.
    
    Returns:
    (total_mention_rate_sum, number_of_groups, total_passes_in_groups)
    """
    groups = group_runs_by_scan_group(runs)
    total_mention_rate = 0.0
    total_groups = 0
    total_passes = 0
    
    for group_id, group_runs in groups.items():
        total_passes += len(group_runs)
        successful_runs = [r for r in group_runs if r.get("status") == "complete"]
        if not successful_runs:
            continue
            
        rate = compute_consensus(group_runs, mentioned_run_ids)
        total_mention_rate += rate
        total_groups += 1
        
    return total_mention_rate, total_groups, total_passes

def get_group_confidence(runs_in_group: List[Dict[str, Any]], mentioned_run_ids: set) -> int:
    """
    Given a list of runs belonging to the same scan_group,
    returns a confidence score (0-100) based on how strictly the passes agreed.
    e.g. 3/3 or 0/3 = 100%. 2/3 = 67%.
    """
    successful_runs = [r for r in runs_in_group if r.get("status") == "complete"]
    if not successful_runs:
        return 0
    mentions = sum(1 for r in successful_runs if r.get("id") in mentioned_run_ids)
    
    rate = float(mentions) / len(successful_runs)
    # Confidence is 100% at rate 0.0 or 1.0, and scales linearly down to 50% at rate 0.5 (if possible).
    # Specifically: max(rate, 1 - rate) * 100
    return int(round(max(rate, 1.0 - rate) * 100))
