from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.chat_models.base import BaseChatModel
from langchain.llms.base import LLM
from langchain.schema.messages import BaseMessage, ChatMessage
from langchain.schema import ChatGeneration, ChatResult
from langchain_community.llms import HuggingFaceEndpoint
from transformers import T5Tokenizer, T5ForConditionalGeneration
from transformers import pipeline, set_seed
from typing import Any, List, Mapping, Optional
from app.secret import HUGGINGFACEHUB_API_TOKEN, MEDITRON_ENDPOINT

MEDITRON_LLM = HuggingFaceEndpoint(
    endpoint_url=MEDITRON_ENDPOINT,
    max_new_tokens=512,
    top_k=10,
    top_p=0.95,
    typical_p=0.95,
    temperature=0.01,
    repetition_penalty=1.03,
    huggingfacehub_api_token=HUGGINGFACEHUB_API_TOKEN
)

class FlanT5(BaseChatModel, LLM):
  tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-large")
  model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-large")

  def __init__(self):
    super().__init__()

  @property
  def _llm_type(self) -> str:
    return "custom"

  def _call(
    self,
    prompt: str,
    stop: Optional[List[str]] = None,
    run_manager: Optional[CallbackManagerForLLMRun] = None,
    **kwargs: Any,
  ) -> str:
    input_ids = self.tokenizer(prompt, return_tensors="pt").input_ids
    outputs = self.model.generate(input_ids, max_new_tokens=64)
    return self.tokenizer.decode(outputs[0])

  def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        # print(f"generate with messages={messages}")
        if len(messages) > 0:
          # TODO: just generates on first message right now
          model_out = self._call(prompt=messages[0].content)

          return ChatResult(generations=[
                        ChatGeneration(
                            text=model_out,
                            message=ChatMessage(role="ai", content=model_out)
                            )
                ])

        return ChatResult()

  @property
  def _identifying_params(self) -> Mapping[str, Any]:
    return {}

class GPT2Medium(BaseChatModel, LLM):  # pydantic base class
  seed = 24
  max_length = 50
  num_return_sequences = 1
  generator = pipeline('text-generation', model='gpt2-medium')

  def __init__(self):
    super().__init__()
    set_seed(self.seed)

  @property
  def _llm_type(self) -> str:
    return "custom"

  def _call(
    self,
    prompt: str,
    stop: Optional[List[str]] = None,
    run_manager: Optional[CallbackManagerForLLMRun] = None,
    **kwargs: Any,
  ) -> str:
    outputs = self.generator(prompt, max_length=self.max_length, num_return_sequences=self.num_return_sequences)
    return str(outputs[0]["generated_text"])  # only 1 output by default

  def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        if len(messages) > 0:
          # TODO: just generates on first message right now
          model_out = self._call(prompt=messages[0].content)

          # TODO: convert GPT-2 output to LangChain ChatResult
          return ChatResult(generations=[
                        ChatGeneration(
                            text=model_out,
                            message=ChatMessage(role="ai", content=model_out)
                            )
                ])

        return ChatResult()

  @property
  def _identifying_params(self) -> Mapping[str, Any]:
    return {}
    
class Dummy(BaseChatModel, LLM):
  response = "Dummy LLM response"

  def __init__(self):
    super().__init__()

  @property
  def _llm_type(self) -> str:
    return "custom"
  
  def _call(
    self,
    prompt: str,
    stop: Optional[List[str]] = None,
    run_manager: Optional[CallbackManagerForLLMRun] = None,
    **kwargs: Any,
  ) -> str:
    return self.response
  
  def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        # print(f"generate with messages={messages}")
        if len(messages) > 0:
          return ChatResult(generations=[
                        ChatGeneration(
                            text=self.response,
                            message=ChatMessage(role="ai", content=self.response)
                            )
                ])

        return ChatResult()

  @property
  def _identifying_params(self) -> Mapping[str, Any]:
    return {}