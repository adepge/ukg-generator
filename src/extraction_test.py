import extraction_module
import os
import re
from pathlib import Path

pdf_dir = "/home/adamg/Documents/Repositories/ukg-generator/corpus/open_access"
pdf_files = [str(p) for p in Path(pdf_dir).glob("*.pdf")]
# Sort the PDF files by number at the start of the filename
pdf_files.sort(key=lambda x: int(re.search(r'\d+', x.split("/")[-1].split(".")[0]).group()))

print(f"Found {len(pdf_files)} PDF files:")
for i, pdf in enumerate(pdf_files, start=1):
    file_path = Path(pdf)
    file_name = file_path.stem
    json_file_path = Path(f"/home/adamg/Documents/Repositories/ukg-generator/src/output/{file_name}/{file_name}.json")
    if json_file_path.exists():
        print(f"JSON file already exists for {i} of {len(pdf_files)}: {pdf}")
        json_file_path_result = json_file_path
    else:
        print(f"Extracting {i} of {len(pdf_files)}: {file_name}")
        json_file_path_result = extraction_module.extract_json_data(file_path=str(file_path))
    txt_file_path = Path(f"/home/adamg/Documents/Repositories/ukg-generator/src/output/{file_name}/{file_name}.txt")
    if txt_file_path.exists():
        print(f"TXT file already exists for {i} of {len(pdf_files)}: {pdf}")
    else:
        print(f"Extracting {i} of {len(pdf_files)}: {file_name}")
        extraction_module.post_process_json_data(json_path=str(json_file_path_result), write_tuples=True, write_references=False, enrich_metadata=False, enrich_references=False)
    print(f"Extracted {file_name}")

# file_path = "/home/adamg/Documents/Repositories/ukg-generator/docs/test/paper3.pdf"
# json_file_path = "/home/adamg/Documents/Repositories/ukg-generator/src/output/paper2/paper2.json"

# # extraction_module.extract_json_data(file_path=file_path)
# extraction_result = extraction_module.post_process_json_data(json_path=json_file_path, write_tuples=True, write_references=False, enrich_metadata=False, enrich_references=False)

# # metadata = extraction_result.metadata
# # print(metadata)

# for section in extraction_result.sections:
#     print(f"{section.heading}: {section.text}  {section.citations}  {section.citations_reference_count} ")

# # for reference_number, main_url, reference_text in extraction_result.to_legacy_output()[1]:
# #     print(f"{reference_number} | {main_url} | {reference_text}")
