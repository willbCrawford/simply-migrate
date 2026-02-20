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

    def execute_query(self, query: str) -> Any:
        """Execute a query against the tenant database"""
        # from sqlalchemy import create_engine, text
        # engine = create_engine(self.get_connection_string())
        # try:
        #     with engine.connect() as conn:
        #         result = conn.execute(text(query))
        #         return result
        # finally:
        #     engine.dispose()
