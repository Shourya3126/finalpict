import requests
import json
import logging

logger = logging.getLogger(__name__)

class KaggleClient:
    def __init__(self, base_url="https://edef-35-197-119-224.ngrok-free.app"):
        # Ensure no trailing slash
        self.base_url = base_url.rstrip('/')
        self.generate_endpoint = f"{self.base_url}/generate"

    def generate(self, prompt, max_new_tokens=1000, temperature=0.7):
        """
        Sends a prompt to the Kaggle endpoint and returns the generated text.
        """
        payload = {
            "prompt": prompt,
            "max_new_tokens": max_new_tokens,
            "temperature": temperature
        }

        try:
            # The Kaggle endpoint expects:
            # POST /generate
            # Body: {"prompt": "...", "max_new_tokens": 100, "temperature": 0.7}
            # Response: {"response": "generated text"}
            
            # Retry up to 2 times on timeout
            last_error = None
            for attempt in range(2):
                try:
                    response = requests.post(self.generate_endpoint, json=payload, timeout=120)
                    response.raise_for_status()
                    result = response.json()
                    return result.get("response", "")
                except requests.exceptions.Timeout as e:
                    logger.warning(f"LLM request timed out (attempt {attempt+1}/2): {e}")
                    last_error = e
                    continue
            
            logger.error(f"LLM request failed after 2 attempts: {last_error}")
            return f"Error: Request timed out after 2 attempts"
        except Exception as e:
            logger.error(f"Kaggle LLM request failed: {e}")
            return f"Error: {str(e)}"

    def chat(self, messages, max_new_tokens=1000, temperature=0.7):
        """
        Formats a chat history (list of dicts with 'role' and 'content') 
        into a Llama-3 prompt structure and sends it to the endpoint.
        """
        # Simple Llama-3 formatting
        # <|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n...<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n...<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n
        
        formatted_prompt = "<|begin_of_text|>"
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            formatted_prompt += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
        
        formatted_prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
        
        return self.generate(formatted_prompt, max_new_tokens, temperature)

    @staticmethod
    def extract_json(text):
        """
        Extracts the LAST valid JSON object from the text.
        Skips nested JSONs to ensure we get the top-level object.
        """
        text = text.strip()
        candidates = []
        
        i = 0
        while i < len(text):
            if text[i] == '{':
                # Attempt to find the matching brace
                stack = 1
                for j in range(i + 1, len(text)):
                    if text[j] == '{':
                        stack += 1
                    elif text[j] == '}':
                        stack -= 1
                    
                    if stack == 0:
                        # Found a balanced block [i : j+1]
                        candidate = text[i : j+1]
                        try:
                            obj = json.loads(candidate)
                            if isinstance(obj, (dict, list)):
                                candidates.append(obj)
                                # SUCCESS: We found a valid JSON.
                                # Advance i to j+1 to skip this block's content 
                                # (and thus ignore any nested JSONs inside it)
                                i = j
                                break
                        except:
                            # Not valid JSON, keep scanning from i+1
                            pass
                        # If stack==0 but invalid, we break the inner loop 
                        # and let the outer loop increment i
                        break
            i += 1
            
        if candidates:
            return candidates[-1]
            
        return None
