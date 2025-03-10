import json
from extractor.extractor import AAPExtractor  # Import your class
from pathlib import Path


root_path = Path(__file__).resolve().parent.parent
data_path = root_path / "data"
file_name =  "WOTO_P02_AAP02E.docx"
output_json = data_path / "extractor_output" / "output.json"

file_path = data_path / file_name

# Initialize the extractor
extractor = AAPExtractor()

# Process the document
extracted_doc = extractor.extract_from_file(str(file_path))

# Save results to JSON
output_path = Path(output_json)
with output_path.open("w", encoding="utf-8") as f:
    json.dump(extracted_doc.model_dump(), f, indent=4, ensure_ascii=False)

print(f"Extraction complete. JSON saved to {output_json}")