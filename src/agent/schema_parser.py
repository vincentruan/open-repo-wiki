from langchain_core.output_parsers.pydantic import PydanticOutputParser

from typing import Union, Type, TypeVar
import re
import asyncio

from pydantic import BaseModel

from src.agent.schema_factory import FolderSchema, FileSchema

T = TypeVar('T', FileSchema, FolderSchema)


class SchemaParser:
    def __init__(self, schema: Type[BaseModel]):
        self.output_parser = PydanticOutputParser(pydantic_object=schema)
        self.format_instructions = self.output_parser.get_format_instructions()
        self.schema_type = schema

    def parse(self, output: str) -> BaseModel:
        filtered_output = self.remove_json_markdown_wrapper(output)
        return self.output_parser.parse(filtered_output)

    def remove_json_markdown_wrapper(self, llm_output: str) -> str:
        match = re.search(r'\{.*\}', llm_output, re.DOTALL)
        if match:
            return match.group(0)
        return llm_output.strip()