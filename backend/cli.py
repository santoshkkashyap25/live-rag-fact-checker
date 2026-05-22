# test_llm_service.py
from pydantic import BaseModel, Field
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.chains import LLMChain
from langchain_community.chat_models import HuggingFaceEndpoint
import os

class Verdict(BaseModel):
    verdict: str = Field(description="Must be exactly: 'True', 'False', or 'Unverifiable'")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Detailed explanation with evidence citations")

# --- Setup Hugging Face LLM ---
LLM_REPO_ID = "mistralai/Mistral-7B-Instruct-v0.2"  # or Zephyr
os.environ["HUGGINGFACEHUB_API_TOKEN"] = ""

llm = HuggingFaceEndpoint(
    repo_id=LLM_REPO_ID,
    temperature=0.2,
    max_new_tokens=150,
    timeout=120
)

# --- Setup prompt and parser ---
parser = PydanticOutputParser(pydantic_object=Verdict)

template = """You are a precise fact-checking AI. Analyze claims against evidence strictly.

Claim: "{claim}"

Evidence:
{evidence}

{format_instructions}

Response (JSON only):"""

prompt = PromptTemplate(
    template=template,
    input_variables=["claim", "evidence"],
    partial_variables={"format_instructions": parser.get_format_instructions()}
)

# --- Create LLMChain ---
chain = LLMChain(llm=llm, prompt=prompt, output_parser=parser)

# --- Example claim and evidence ---
claim = "The Eiffel Tower is in Berlin"
evidence = ["The Eiffel Tower is located in Paris, France"]

# --- Run chain ---
result = chain.run({"claim": claim, "evidence": "\n".join(evidence)})

# --- Print result ---
print(result)
