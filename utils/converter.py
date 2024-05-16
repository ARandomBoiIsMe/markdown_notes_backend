import marko

def markdown_to_html(markdown):
    return marko.convert(markdown)