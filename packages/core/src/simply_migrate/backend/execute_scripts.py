from sqlalchemy import Engine, text
from typing import Dict

def execute_script(
        engine: Engine,
        script_content: str,
        statement_timeout: int = 10
) -> Dict:
    """Execute a migration script for a tenant"""
    with engine.connect() as conn:
        with conn.begin() as trans:
            try:
                if statement_timeout > 0:
                    conn.execute(text(f"SET statement_timeout = '{statement_timeout}s'"))

                conn.execute(text(script_content))
                trans.commit()
                return {"success": True, "message": "Script executed successfully"}
            except Exception as e:
                trans.rollback()
                raise e