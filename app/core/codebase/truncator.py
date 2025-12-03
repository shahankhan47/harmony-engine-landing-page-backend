import tiktoken
from app.constants import ANTHROPIC_CLIENT


async def open_ai_truncator(text: str, model: str, max_tokens: int):
    try:
        # Initialize the tokenizer
        enc = tiktoken.get_encoding("o200k_base")
        
        # Encode the text to tokens
        tokens = enc.encode(text)
        
        # Check if the number of tokens is within the limit
        if len(tokens) <= max_tokens:
            print(f'length of untruncated file: {len(tokens)}')
            return text
        
        # If too long, truncate and decode the tokens
        else:
            print('file truncated')
            return enc.decode(tokens[:max_tokens])
        
    except Exception as e:
        # Log the exception details
        print(f"An error occurred during truncation: {str(e)}")
        return None

def anthropic_truncator(text, max_tokens=160000, model="claude-haiku-4-5"):
    """Use binary search to efficiently truncate text to fit token limit."""
    
    # Initial check
    count = ANTHROPIC_CLIENT.messages.count_tokens(
        model=model,
        messages=[{"role": "user", "content": text}]
    )
    
    if count.input_tokens <= max_tokens:
        return text
    
    # Binary search for the right length
    low = 0
    high = len(text)
    
    while high - low > 5000:  # Stop when we're close enough
        mid = (low + high) // 2
        truncated = text[:mid]
        
        count = ANTHROPIC_CLIENT.messages.count_tokens(
            model=model,
            messages=[{"role": "user", "content": truncated}]
        )
        
        if count.input_tokens <= max_tokens:
            low = mid
        else:
            high = mid
    
    # Fine-tune the final result
    while True:
        truncated = text[:high]
        count = ANTHROPIC_CLIENT.messages.count_tokens(
            model=model,
            messages=[{"role": "user", "content": truncated}]
        )
        
        if count.input_tokens <= max_tokens:
            return truncated
        
        high -= 5000  # Reduce by 5000 characters at a time until we fit