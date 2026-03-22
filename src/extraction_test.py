import extraction_module

file_path = "/home/adamg/Documents/Repositories/ukg-generator/docs/test/paper4.pdf"
json_file_path = "/home/adamg/Documents/Repositories/ukg-generator/src/output/paper4/paper4.json"

# extraction_module.extract_json_data(file_path=file_path)
extraction_result = extraction_module.post_process_json_data(json_path=json_file_path, write_tuples=True, write_references=False, enrich_metadata=True)

# metadata = extraction_result.metadata
# print(metadata)

for section in extraction_result.sections:
    print(f"{section.heading}: {section.text}  {section.citations} ")

# for reference_number, main_url, reference_text in extraction_result.to_legacy_output()[1]:
#     print(f"{reference_number} | {main_url} | {reference_text}")
