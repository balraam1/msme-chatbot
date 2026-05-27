import re

def format_whatsapp_message(text: str) -> str:
    """
    Formats HTML and Markdown response texts to match WhatsApp markup:
    - Bold: Markdown **text** -> WhatsApp *text*
    - Italic: Markdown *text* or _text_ -> WhatsApp _text_
    - Strikethrough: Markdown ~~text~~ -> WhatsApp ~text~
    - Headers: # Header -> *Header*
    - HTML: <br> -> \n, <b>/<strong> -> *, <i>/<em> -> _, other tags stripped
    - Links: [Text](URL) -> Text (URL)
    """
    if not text:
        return ""
    
    # 1. Handle HTML tags
    # Replace line breaks
    text = re.sub(r'<br\s*/?>', '\n', text)
    # Replace bold tags
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'*\1*', text)
    text = re.sub(r'<b[^>]*>(.*?)</b>', r'*\1*', text)
    # Replace italic tags
    text = re.sub(r'<em[^>]*>(.*?)</em>', r'_\1_', text)
    text = re.sub(r'<i[^>]*>(.*?)</i>', r'_\1_', text)
    # Strip any other HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # 2. Handle Markdown links
    # Replace [Text](URL) with "Text (URL)"
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1 (\2)', text)
    
    # 3. Handle Markdown headers
    # Convert "# Header Name" to "*Header Name*"
    text = re.sub(r'^#+\s+(.*?)$', r'*\1*', text, flags=re.MULTILINE)
    
    # 4. Handle Markdown Bold / Italic conversion
    # Markdown bold: **word** -> WhatsApp bold: *word*
    # Markdown italic: *word* -> WhatsApp italic: _word_
    # To do this safely without conflict, use place holders.
    
    # Protect existing bold blocks
    text = re.sub(r'\*\*(.*?)\*\*', r'__BOLD_TEMP__\1__BOLD_TEMP__', text)
    
    # Convert markdown italics: *italic* -> _italic_
    text = re.sub(r'\*(.*?)\*', r'_\1_', text)
    
    # Convert protected bold blocks to WhatsApp bold *
    text = text.replace('__BOLD_TEMP__', '*')
    
    # Handle strikethrough: ~~word~~ -> ~word~
    text = re.sub(r'~~(.*?)~~', r'~\1~', text)
    
    # Clean up double spacing and strip extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
