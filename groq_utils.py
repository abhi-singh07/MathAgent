def extract_text(response):
    """
    Extract text from Groq response in a way that matches OpenAI's format.
    """
    return [response.choices[0].message.content]