import pymupdf.layout
import pymupdf4llm
import json
import pandas

file_path = "/home/adamg/Documents/Repositories/ukg-generator/docs/test/paper.pdf"
json_file_path = "/home/adamg/Documents/Repositories/ukg-generator/docs/test/output.json"
txt_file_path = "/home/adamg/Documents/Repositories/ukg-generator/docs/test/output.txt"
images_path = "/home/adamg/Documents/Repositories/ukg-generator/docs/test/images"

doc = pymupdf.open(file_path) # open a document

json = pymupdf4llm.to_json(doc, image_path=images_path, write_images=True, show_progress=True, use_ocr=False)

# for page in doc: # iterate the document pages
#     text = page.get_text("blocks") # get plain text (is in UTF-8)

#     for x0, y0, x1, y1, block, block_no, block_type in text:
#         if block_type == 0:
#             encoded_text = block.encode('utf8')
#             out.write(encoded_text)
#     #out.write(bytes((12,))) # write page delimiter (form feed 0x0C)
out = open(json_file_path, "wb") # create a text output
out.write(json.encode("utf-8"))
out.close()