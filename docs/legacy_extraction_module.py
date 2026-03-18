import nltk
import pymupdf.layout
import pymupdf4llm
import json
import string
import pandas
import re
from collections import Counter
from pathlib import Path

def extract_json_data(file_path: str):
    """
    Extracts the data from PDF file and generates a JSON file.
    """
    file_name = file_path.split("/")[-1].split(".")[0]

    # Create output directory for paper data
    output_dir = Path(__file__).parent / "output" / file_name
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{file_name}.json"

    # Extract data from PDF file
    try:
        doc = pymupdf.open(file_path)
    except Exception as e:
        print(f"Error: {e}")
        return None

    json = pymupdf4llm.to_json(doc, image_path=str(output_dir), write_images=True, show_progress=True, use_ocr=False)

    # Save JSON file
    with open(output_path, "w") as f:
        json.dump(json, f)

    return output_path

def post_process_json_data(json_path: str, write_tuples: bool = False, write_references: bool = False):
    """
    Post processes the JSON data to generate a tuples file.
    Args:
        json_path: Path to the JSON file.
        write_tuples: Whether to write the tuples file.
    Returns:
        A list of tuples (heading, text).
    """
    with open(json_path, "r") as f:
        data = json.load(f)

    file_name = json_path.split("/")[-1].split(".")[0]
    folder_path = "/".join(json_path.split("/")[:-1])
    text_file = folder_path + "/" + file_name + ".txt"
    reference_file = folder_path + "/" + file_name + ".references.txt"

    font_sizes = Counter()
    heading_sizes = {}
    title = ""
    current_heading = ""
    metadata_heading = ""
    reference_list = []
    results = []

    # Get most common font size of text lines
    for page in data.get("pages", []):
        for box in page.get("boxes", []):
            boxclass = box.get("boxclass", "")
            if boxclass == "text":
                for textline in box.get("textlines", []):
                    for span in textline.get("spans", []):
                        size = span.get("size", 0)
                        font_sizes[size] += 1

            if boxclass == "section-header":
                for textline in box.get("textlines", []):
                    for span in textline.get("spans", []):
                        size = span.get("size", 0)
                        heading_sizes[size] = heading_sizes.get(size, 0) + 1

    # Using frequency we can find the most common font size
    # This should correspond to the body text size
    standard_text_size = font_sizes.most_common(1)[0][0]

    # The largest heading size should correspond to the title
    title_size = max(heading_sizes.keys())

    for i, page in enumerate(data.get("pages", [])):
        for box in page.get("boxes", []):
            boxclass = box.get("boxclass", "")

            if boxclass == "section-header":
                # Get the first span's info (main heading info)
                for textline in box.get("textlines", []):
                    for span in textline.get("spans", []):
                        size = span.get("size", 0)
                        heading = span.get("text", "").strip()
                        font = span.get("font", "")
                        if size < standard_text_size:
                            continue
                        else:
                            current_heading = heading
            
            if boxclass == "text":
                if len(current_heading) < 1:
                    continue

                full_text = ""
                last_text = results[-1][1] if results else None
                if last_text and last_text[-1] not in ".!?":
                    merge_text = True
                else:
                    merge_text = False

                for textline in box.get("textlines", []):
                    for span in textline.get("spans", []):
                        size = span.get("size", 0)
                        if size < standard_text_size:
                            continue
                        else:
                            new_text = span.get("text", "").strip()                            
                            if not full_text:
                                full_text = new_text
                            elif full_text and full_text[-1] == "-":
                                full_text = full_text[:-1] + new_text
                            else:
                                full_text += " " + new_text

                # Remove any leading or trailing whitespace
                full_text = full_text.strip().replace("�", "")

                if merge_text:
                    results[-1] = (current_heading, results[-1][1] + full_text)
                else:
                    if full_text:
                        results.append((current_heading, full_text))
            
            if boxclass == "list-item" and current_heading.lower() in ["references", "reference list", "citations", "bibliography"]:
                reference_list.extend(extract_references(data, i))
                print("test")
                break
        if reference_list:
            break
                
    
    if write_tuples:
        with open(text_file, "w") as f:
            for heading, text in results:
                f.write(f"{heading}: {text}\n")

    if write_references:
        with open(reference_file, "w") as f:
            for reference_number, main_url, reference_text in reference_list:
                f.write(f"{reference_number} | {main_url} | {reference_text}\n")

    #results = associate_citations(results)

    return results, reference_list

def extract_references(data: dict, page_number: int) -> list[tuple[int, str]]:
    """
    Extracts the references from the JSON data.
    Args:
        data: The JSON data.
        page_number: The page number.
    Returns:
        A list of tuples (reference_number, reference).
    """
    reference_list = []
    reference_number = 0
    skip_reference = True
    pages = data.get("pages", [])[page_number:]
    for page in pages:
        for box in page.get("boxes", []):
            boxclass = box.get("boxclass", "")
            if boxclass == "list-item":
                full_text = ""
                for textline in box.get("textlines", []):
                    for span in textline.get("spans", []):
                        new_text = span.get("text", "").strip()
                        if len(new_text) < 4:
                            number = new_text.replace(".", "")
                            if number.isdigit():
                                skip_reference = False
                                reference_number = int(number)
                                continue
                            else:
                                skip_reference = True
                        else:
                            if skip_reference:
                                continue
                            if full_text and full_text[-1] == "-":
                                full_text = full_text[:-1] + new_text
                            elif check_url_characters(full_text) and not new_text.startswith("PMID"):
                                full_text += new_text
                            else:
                                full_text += " " + new_text
                    full_text = full_text.strip().replace("�", "")
                if full_text:
                    reference_list.append((reference_number, full_text))
            
            # Handle the cases where the references are detected as a table
            if boxclass == "table":
                table = box.get("table", {})
                table_data = table.get("extract", [])
                if reference_list and reference_list[-1][1][-1] not in ".!?":
                    reference_number = reference_list[-1][0]
                    full_text = reference_list[-1][1]
                    append_last = True
                else:
                    reference_number = None
                    full_text = ""
                    append_last = False
                for row in table_data:
                    if len(row[0].strip()) < 4:
                        number = row[0].replace(".", "")
                        if number.isdigit():
                            if reference_number is not None:
                                if append_last:
                                    reference_list[-1] = (reference_number, reference_list[-1][1] + full_text.strip())
                                    append_last = False
                                else:
                                    reference_list.append((reference_number, full_text.strip().replace("�", "")))
                            reference_number = int(number)
                            full_text = ""
                    
                    # If the last character is a hyphen, combine the next textline without a space
                    if full_text and full_text[-1] == "-":
                        full_text = full_text[:-1] + row[1]
                    # If the last 10 characters contain at least two of the following characters, combine the next textline without a space
                    elif check_url_characters(full_text[-10:]) and not row[1].startswith("PMID"):
                        full_text += row[1]
                    # Otherwise, combine the next textline with a space
                    else:
                        full_text += " " + row[1]
                if full_text:
                    if reference_number is not None:
                        reference_list.append((reference_number, full_text.strip().replace("�", "")))

    references = []
    for reference_number, reference_text in reference_list:
        urls = re.findall(r'https?://[^\s]+', reference_text)
        if urls:
            main_url = max(urls, key=len)
        else:
            main_url = None
        references.append((reference_number, main_url, reference_text))
    return references

def check_url_characters(text: str) -> bool:
    """
    Checks if the last 10 characters contain at least two of the following characters: /, ., :
    """
    count = 0
    for char in text:
        if char in ["/", ".", ":", "?", "="]:
            count += 1
    return count >= 2

def associate_citations(results: list[tuple[str, str]]) -> list[tuple[str, str, list[int]]]:
    """
    Associates the citations in results with the references in reference_list.
    Args:
        results: The results.
    Returns:
        A list of tuples (heading, text, citations).
    """
    citation_litmus = results[:3]
    extract_citations = False
    for heading, text in citation_litmus:
        if re.search(r'\[\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*\]', text):
            extract_citations = True
            break
    if not extract_citations:
        return results

    new_results = []
    for heading, text in results:
        citation_numbers = []
        citation_pattern = r'\[\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*\]'
        matches = re.findall(citation_pattern, text)
        for match in matches:
            numbers = match[1:-1]
            if "," and "-" in numbers:
                match_numbers = numbers.split(",")
                for number in match_numbers:
                    if "-" in number:
                        range_numbers = number.split("-")
                        for range_number in range(int(range_numbers[0]), int(range_numbers[1]) + 1):
                            citation_numbers.append(range_number)
                    else:
                        citation_numbers.append(int(number))         
            elif "," in numbers:
                match_numbers = numbers.split(",")
                for number in match_numbers:
                    citation_numbers.append(int(number))
            elif "-" in numbers:
                range_numbers = numbers.split("-")
                for number in range(int(range_numbers[0]), int(range_numbers[1]) + 1):
                    citation_numbers.append(number)
            else:
                citation_numbers.append(int(numbers))
        new_results.append((heading, text, citation_numbers))

        # Remove all citation numbers from text
        text = re.sub(citation_pattern, "", text)
    return new_results