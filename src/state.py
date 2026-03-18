from pydantic import BaseModel
from pydantic import Field

from agent import Action
from typing import Union, Optional, Any, List, Dict, Tuple
from agentspec_codegen.runtime import RuleRuntimeContext
 
class RuleState(BaseModel):
    toolkit: str = ""
    action: Optional[Action] = None
    agent: Optional[Any] = None
    intermediate_steps: Any #todo: List[Tuple[AgentAction, str]]
    user_input: Optional[Union[str, Dict[str, Any]]] = None # task_prompt
    run_mannager: Optional[Any] = None
    merits: List[str] = Field(default_factory=list)
    critiques: List[str] = Field(default_factory=list)
    reflection_depth:int = 0
    runtime_context: RuleRuntimeContext = Field(default_factory=RuleRuntimeContext)

    def add_merit(self, m: str):
        self.merits.append(m) 

    def set_critique(self, c: str):
        self.critiques.append(c) 