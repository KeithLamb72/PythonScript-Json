# python
import json
import re
import csv
import os
from collections import defaultdict

def load_json(file_path):
    """
    Loads JSON data from the given file path.
    Returns the data as a dictionary or None if an error occurs.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return None

def extract_urls(json_data):
    """
    Recursively searches through the JSON data and extracts all URLs.
    Returns a list of unique URLs.
    """
    urls = []

    def search(obj):
        if isinstance(obj, dict):
            for value in obj.values():
                search(value)
        elif isinstance(obj, list):
            for item in obj:
                search(item)
        elif isinstance(obj, str):
            # Look for patterns starting with http:// or https://
            found = re.findall(r"https?://\S+", obj)
            urls.extend(found)

    search(json_data)
    return list(set(urls))  # Remove duplicates

def extract_chain_of_thought(json_data):
    """
    Retrieves the chain_of_thought list from the top-level JSON.
    If not present, returns an empty list and logs a warning.
    """
    if "chain_of_thought" not in json_data:
        print("Warning: 'chain_of_thought' key not found in JSON. Using an empty list.")
    return json_data.get("chain_of_thought", [])

def extract_tool_executions(json_data):
    """
    Extracts all tool execution details from the chain_of_thought.
    (This is where information for Maps, Flights, Hotels, etc. can be found.)
    Returns a list of tool execution dictionaries.
    """
    tool_execs = []
    chain = extract_chain_of_thought(json_data)
    for step in chain:
        if "tool_executions" in step:
            for exec_data in step["tool_executions"]:
                tool_execs.append(exec_data)
    return tool_execs

def sort_urls_by_relevance(urls, keywords=None):
    """
    Sorts the list of URLs based on a relevance score.
    The score is based on the occurrence of keywords.
    By default the keywords list includes terms that might appear in Maps, Flights, Hotels, etc.
    """
    if keywords is None:
        keywords = ["maps", "flights", "hotels", "booking", "price", "search", "showtimes"]
    url_relevance = defaultdict(list)
    for url in urls:
        # Count how many keywords appear in the URL (case-insensitive)
        score = sum(1 for keyword in keywords if keyword in url.lower())
        url_relevance[score].append(url)
    sorted_urls = []
    for score in sorted(url_relevance.keys(), reverse=True):
        sorted_urls.extend(url_relevance[score])
    return sorted_urls

def flatten_tool_execution(exec_data):
    """
    Flattens a tool execution dictionary so that it can be saved easily in CSV.
    For example, it converts the 'params' and 'output' (which might be nested) into JSON strings.
    """
    return {
        "tool_name": exec_data.get("tool_name", ""),
        "method_name": exec_data.get("method_name", ""),
        "params": json.dumps(exec_data.get("params", {})),
        "output": json.dumps(exec_data.get("output", []))
    }

def save_to_json(data, output_file):
    """
    Saves the given data structure to a JSON file.
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving to JSON: {e}")

def save_to_csv(data, output_file, headers):
    """
    Saves a list of dictionaries to a CSV file using the provided headers.
    """
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)
    except Exception as e:
        print(f"Error saving to CSV: {e}")

def main(input_file, output_folder=None):
    # Determine the output folder (defaults to current directory)
    if output_folder is None:
        output_folder = "."
    else:
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
    
    # Load the JSON data
    json_data = load_json(input_file)
    if not json_data:
        return

    # Extract top-level metadata if available
    metadata = {
        "location": json_data.get("location", ""),
        "time": json_data.get("time", ""),
        "error": json_data.get("error", ""),
        "observation": json_data.get("observation", "")
    }

    # Extract chain_of_thought and tool executions
    chain = extract_chain_of_thought(json_data)
    tool_execs = extract_tool_executions(json_data)

    # Flatten tool executions for CSV export
    flat_tool_execs = [flatten_tool_execution(exec_data) for exec_data in tool_execs]

    # Extract and sort all URLs in the file
    all_urls = extract_urls(json_data)
    sorted_urls = sort_urls_by_relevance(all_urls)
    
    if not sorted_urls:
        print("No URLs were found in the JSON data.")

    # Compile all extracted information into a single structure
    output_data = {
        "metadata": metadata,
        "chain_of_thought": chain,
        "tool_executions": tool_execs,
        "sorted_urls": sorted_urls
    }

    # Define paths for output files
    json_output = os.path.join(output_folder, "extracted_data.json")
    tool_csv_output = os.path.join(output_folder, "tool_executions.csv")
    urls_csv_output = os.path.join(output_folder, "urls.csv")

    # Save the combined data to a JSON file
    save_to_json(output_data, json_output)

    # Save tool execution details to a CSV file (if any)
    if flat_tool_execs:
        headers = flat_tool_execs[0].keys()
        save_to_csv(flat_tool_execs, tool_csv_output, headers)
    else:
        print("No tool execution details found to export.")

    # Save the sorted URLs to a CSV file
    if sorted_urls:
        url_rows = [{"url": url} for url in sorted_urls]
        save_to_csv(url_rows, urls_csv_output, headers=["url"])

    print("Data extraction complete. Files saved:")
    print("  -", json_output)
    if flat_tool_execs:
        print("  -", tool_csv_output)
    if sorted_urls:
        print("  -", urls_csv_output)

if __name__ == "__main__":
    # Example usage:
    # You can replace 'input.json' with your JSON file path
    # Optionally, pass a second argument for the output folder (e.g., "output_files")
    import sys
    if len(sys.argv) > 1:
        input_filepath = sys.argv[1]
    else:
        input_filepath = "input.json"
    
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    main(input_filepath, output_dir)