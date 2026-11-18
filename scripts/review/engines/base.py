"""Abstract Reviewer Engine Adapter."""
import abc
from typing import List, Dict, Tuple, Optional, Any

class ReviewEngineAdapter(abc.ABC):
    @abc.abstractmethod
    def resolve_binary(self) -> List[str]:
        raise NotImplementedError("Subclasses must implement resolve_binary")

    @abc.abstractmethod
    def build_command(
        self,
        launcher_cmd: List[str],
        repo_path: str,
        schema_path: str,
        review_file_path: str,
        prompt_text: str,
        session_id: Optional[str],
        model: Optional[str]
    ) -> List[str]:
        raise NotImplementedError("Subclasses must implement build_command")

    @abc.abstractmethod
    def get_execution_environment(self) -> Dict[str, str]:
        raise NotImplementedError("Subclasses must implement get_execution_environment")

    @abc.abstractmethod
    def extract_review_payload_and_session(
        self,
        stdout_path: str,
        stderr_path: str,
        review_file_path: str,
        prior_session_id: Optional[str]
    ) -> Tuple[Dict[str, Any], str]:
        raise NotImplementedError("Subclasses must implement extract_review_payload_and_session")
