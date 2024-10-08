from openai import OpenAI
import os
import csv
import re
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env file
_ = load_dotenv(find_dotenv())

# Set up your OpenAI API key
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI()

# Function to read markdown files from a directory
def read_markdown_files(directory):
    markdown_files = {}
    for filename in os.listdir(directory):
        if filename.endswith('.md'):
            with open(os.path.join(directory, filename), 'r') as file:
                markdown_files[filename] = file.read()
    return markdown_files

# Function to generate questions and answers using GPT-4 API
def generate_qa_from_markdown(markdown_content):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": f"Read the following markdown content and generate sensible and deeply thought-out questions and corresponding answers:\n\n{markdown_content}\n\nQuestions and Answers:"}],
            max_tokens=1500,
            n=1,
            stop=None,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating QA: {e}")
        return ""

# Function to format Q&A pairs from the generated text
def parse_qa_text(qa_text):
    qa_pairs = []
    pattern = re.compile(r"### Question \d+: (.*?)\n\n\*\*Answer:\*\* (.*?)(?:\n---|\Z)", re.DOTALL)
    
    matches = pattern.findall(qa_text)
    for match in matches:
        question, answer = match
        # print(question, answer)
        qa_pairs.append((question.strip(), answer.strip()))
    
    return qa_pairs

# Main function to process all markdown files in a directory and append Q&A to CSV
def process_markdown_directory(directory, output_csv):
    markdown_files = read_markdown_files(directory)
    
    with open(output_csv, 'a', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(['Filename', 'Question', 'Answer'])

        for filename, content in markdown_files.items():
            print(f"Processing file: {filename}")
            qa_text = generate_qa_from_markdown(content)
            if qa_text:
                qa_pairs = parse_qa_text(qa_text)
                for question, answer in qa_pairs:
                    csvwriter.writerow([question, answer])
            else:
                print(f"No QA generated for file: {filename}")

# Example usage
directory_path = 'data'
output_csv_path = 'qanda.csv'
process_markdown_directory(directory_path, output_csv_path)

print(f"Q&A pairs have been successfully written to {output_csv_path}")
