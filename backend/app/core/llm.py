import os
import logging
import time
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)

class LLMService:
    """
    Singleton initialization for the Groq LLM (llama-3.3-70b-versatile).
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            logger.info("Initializing Groq LLM: llama-3.3-70b-versatile")
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key or api_key == "your_key_here":
                logger.warning("GROQ_API_KEY is not set properly in .env.")
                
            cls._instance = super(LLMService, cls).__new__(cls)
            
            try:
                cls._instance.llm = ChatGroq(
                    model="llama-3.3-70b-versatile",
                    api_key=api_key,
                    temperature=0.1,  # Low temperature for highly factual/grounded answers
                    max_tokens=2048
                )
            except Exception as e:
                logger.error(f"Failed to initialize Groq LLM: {str(e)}")
                cls._instance.llm = None
        return cls._instance

    def generate_response(self, prompt: str) -> str:
        """
        Generates a grounded response using the initialized Groq LLM.
        """
        if not self.llm:
            raise RuntimeError("LLM is not properly initialized. Check your API key.")
            
        start_time = time.time()
        logger.info("Sending prompt to LLM for answer generation...")
        
        try:
            response = self.llm.invoke(prompt)
            elapsed = time.time() - start_time
            logger.info(f"LLM response generated successfully in {elapsed:.2f} seconds.")
            # Note: logging token usage requires checking response_metadata which depends on the exact wrapper
            return response.content
        except Exception as e:
            logger.error(f"LLM API failure: {str(e)}")
            raise e

def get_llm_service() -> LLMService:
    return LLMService()
