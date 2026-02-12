import json
from collections import Counter

json_file_path = "/home/adamg/Documents/Repositories/ukg-generator/docs/test/output.json"
txt_file_path = "/home/adamg/Documents/Repositories/ukg-generator/docs/test/tuples.txt"
extra_txt_file_path = "/home/adamg/Documents/Repositories/ukg-generator/docs/test/extra.txt"

# Post processing with json
try:
    with open(json_file_path, "r") as json_data:
        data = json.load(json_data)
except FileNotFoundError:
    print(f"Error: The file {json_file_path} was not found")
except json.JSONDecodeError:
    print("Error: Failed to decode JSON from the file.")


font_sizes = Counter()
heading_sizes = {}

# Get most common font size of text lines
for page in data.get("pages", []):
    for box in page.get("boxes", []):
        boxclass = box.get("boxclass", "")
        if boxclass == "text":
            for textline in box.get("textlines", []):
                for span in textline.get("spans", []):
                    size = span.get("size", 0)
                    text = span.get("text", "").strip()
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

title = ""
current_heading = ""
metadata_heading = ""
results = []


for page in data.get("pages", []):
    page_width = page.get("width", 0)
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
                    

with open(txt_file_path, "w") as txt_file:
    for heading, text in results:
        txt_file.write(f"{heading}: {text}\n")

# sections = {}
# for page in data.get("pages", []):
#     for box in page.get("boxes", []):
#         if box["boxclass"] == "section-header":
#             sections[box["textlines"][0]["spans"][0]["text"]] = box["textlines"][1]["text"]
#         elif box["boxclass"] == "section-text":
#             sections[box["textlines"][0]["spans"][0]["text"]] = box["textlines"][1]["text"]

# print(sections)
