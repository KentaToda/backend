from typing import Optional
from typing_extensions import TypedDict

from backend.features.agent.vision.schema import InitialAnalysis

class AgentState(TypedDict):
    messages: list
    analysis_result: Optional[InitialAnalysis] # node_visionの結果
    search_results: Optional[str]              # Node Bの結果
    retry_count: int                           # リトライ回数