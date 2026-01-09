from typing import Optional
from typing_extensions import TypedDict

from backend.features.agent.vision.schema import InitialAnalysis
from backend.features.agent.search.schema import SearchNodeOutput
from backend.features.agent.price.schema import PriceNodeOutput


class AgentState(TypedDict):
    messages: list
    analysis_result: Optional[InitialAnalysis]  # node_visionの結果
    search_output: Optional[SearchNodeOutput]   # node_searchの結果
    price_output: Optional[PriceNodeOutput]     # node_priceの結果
    retry_count: int                            # リトライ回数