import nltk
import pymupdf.layout
import pymupdf4llm
import json
import pandas
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

    json = pymupdf4llm.to_json(doc, image_path=output_dir, write_images=True, show_progress=True, use_ocr=False)

    # Save JSON file
    with open(output_path, "w") as f:
        json.dump(json, f)

    return output_path

def post_process_json_data(json_path: str, write_tuples: bool = False):
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
    folder_path = "".join(json_path.split("/")[:-1])
    text_file = folder_path / file_name

    font_sizes = Counter()
    heading_sizes = {}
    title = ""
    current_heading = ""
    metadata_heading = ""
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

    for page in data.get("pages", []):
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
                            full_text += span.get("text", "").strip()
                
                if merge_text:
                    results[-1] = (current_heading, results[-1][1] + full_text)
                else:
                    if full_text:
                        results.append((current_heading, full_text))
    
    if write_tuples:
        with open(text_file, "w") as f:
            for heading, text in results:
                f.write(f"{heading}: {text}\n")

    return results