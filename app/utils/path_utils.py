import base64
import binascii # Import for error handling

def encode_path(path: str) -> str:
    """Encodes a file path into a URL-safe base64 string."""
    if not isinstance(path, str):
        raise TypeError("Path must be a string")
    return base64.urlsafe_b64encode(path.encode('utf-8')).decode('utf-8')

def decode_path(encoded: str) -> str:
    """Decodes a URL-safe base64 string back into a file path."""
    if not isinstance(encoded, str):
        raise TypeError("Encoded path must be a string")
    try:
        # Add padding if necessary, as base64 requires it
        padded_encoded = encoded + '=' * (-len(encoded) % 4)
        return base64.urlsafe_b64decode(padded_encoded.encode('utf-8')).decode('utf-8')
    except (binascii.Error, UnicodeDecodeError) as e:
        raise ValueError(f"Invalid base64 encoded path: {encoded}. Error: {e}")