from src.llm.llm_config import LLMConfig
from src.llm.llm_provider import LLMProvider
from src.llm.providers.deepseek import DeepSeekProvider
from src.llm.providers.openrouter import OpenRouterProvider

import os
import dotenv

dotenv.load_dotenv()

LLMEnvConfig = {
    "provider": os.getenv('LLM_PROVIDER'),
    "apiKey": os.getenv('LLM_APIKEY'),
    "modelName": os.getenv('LLM_MODELNAME')
}


class LLMFactory:
    @staticmethod
    def create_provider(llm_config: LLMConfig) -> LLMProvider:
        provider = LLMEnvConfig.get('provider')
        if not provider:
            raise Exception(
                'LLM Provider is not specified. Please set LLM_PROVIDER in the environment\nExample: '
                'LLM_PROVIDER=openrouter, LLM_PROVIDER=deepseek')

        model_name = LLMEnvConfig.get('modelName')
        if not model_name:
            raise Exception('LLM Model name is not specified. Example: LLM_MODELNAME=llama3.3 for llama3.3')

        api_key = LLMEnvConfig.get('apiKey')
        if not api_key:
            raise Exception('LLM API key is not specified. Please set LLM_APIKEY in the environment')

        match provider:
            case 'deepseek':
                return DeepSeekProvider(api_key=api_key, model_name=model_name, llm_config=llm_config)
            case 'openrouter':
                return OpenRouterProvider(api_key=api_key, model_name=model_name, llm_config=llm_config)
            case _:
                raise Exception('Unsupported LLM Provider')
