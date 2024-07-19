import requests

def scrape_text_to_markdown(url, output_file):
    response = requests.get(url)
    response.raise_for_status()  # Ensure we notice bad responses
    content = response.text
    
    with open(output_file, 'w', encoding='utf-8') as file:
        # Assuming the text file does not have HTML tags and can be written directly
        file.write(content)
    
    print(f"Content saved to {output_file}")

# URL to scrape
url = 'https://www.projectwittenberg.org/pub/resources/text/wittenberg/concord/web/smc-01.html'
# Output file
output_file = 'small_cald_articles.md'
scrape_text_to_markdown(url, output_file)


# for i in range(1, 16):
#     url = f'https://www.projectwittenberg.org/pub/resources/text/wittenberg/luther/catechism/web/cat-{i:02}.html'
#     output_file = f'large_cath-{i:02}.md'
#     scrape_text_to_markdown(url, output_file)