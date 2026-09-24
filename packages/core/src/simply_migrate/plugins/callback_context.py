from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class CallbackContext:
    """Context passed to callback functions"""
    job_id: str
    tenant_id: str
    script: Dict
    scripts: List[Dict]
    current_script_index: int
    metadata: Dict[str, Any]  # User-defined metadata