from antlr4 import *
import unittest
from enum import Enum
from typing import Any
from pydantic import BaseModel 
from spec_lang.AgentSpecListener import AgentSpecListener 
from spec_lang.AgentSpecLexer import AgentSpecLexer
from spec_lang.AgentSpecParser import AgentSpecParser  

# ---------------------------------------------------------------------------
# Per-process parse-tree cache – avoids re-lexing/parsing the same .spec text
# across many evaluation cases.
# ---------------------------------------------------------------------------
_parse_tree_cache: dict[str, Any] = {}


def _get_or_parse_tree(rule_raw: str) -> Any:
    if rule_raw in _parse_tree_cache:
        return _parse_tree_cache[rule_raw]
    input_stream = InputStream(rule_raw)
    lexer = AgentSpecLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = AgentSpecParser(token_stream)
    tree = parser.program()
    _parse_tree_cache[rule_raw] = tree
    return tree


def clear_parse_tree_cache() -> None:
    _parse_tree_cache.clear()  

class RuleParser(AgentSpecListener): 
   
    event: str
    
    def enterTriggerClause(self, ctx):
        self.event = ctx.event().getText()
         
    def enterRuleClause(self, ctx):
        self.id = ctx.IDENTIFIER(). getText()
             
    def getId(self):
        return self.id

class Rule(BaseModel):
    id: str
    event: str 
    raw: str
     
    def triggered(self, action_name, input:str):  
        return self.event == "any" or action_name == self.event or input.strip().startswith(self.event.replace("_",' '))
    
    def trigger_finished(self):
        return self.event=="finish"
    
    def from_text(rule_str):
        input_stream = InputStream(rule_str)
        lexer = AgentSpecLexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = AgentSpecParser(token_stream)

        tree = parser.program()
        walker = ParseTreeWalker()
        rule_parser = RuleParser()
        walker.walk(rule_parser, tree)   
        return Rule(raw=rule_str, event=rule_parser.event, id=rule_parser.getId())
 