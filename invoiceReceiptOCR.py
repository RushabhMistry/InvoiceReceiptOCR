from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import tabula
import fitz  # PyMuPDF
import re
import pandas as pd
import os

app = FastAPI()

# Function to extract text from PDF using PyMuPDF
def extract_text(pdf_path):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

# Function to extract tables from PDF using tabula
def extract_tables(pdf_path):
    tables = tabula.read_pdf(pdf_path, pages="all", multiple_tables=True, guess=True)
    return tables

# Function to save tables to Excel
def save_tables_as_excel(tables):
    file_paths = []
    for idx, table in enumerate(tables):
        file_path = f"table_{idx+1}.xlsx"
        table.to_excel(file_path, index=False)
        file_paths.append(file_path)
    return file_paths

# Define patterns for key information extraction
patterns = {
    "To": r"To[:\s]*([^\n\r]+)",
    "From": r"From[:\s]*([^\n\r]+)",
    "Transaction ID": r"Transaction\s*ID[:\s]*([\w-]+)",
    "Payment Mode": r"Payment\s*Mode[:\s]*([^\n\r]+)",
    "Payment Date": r"Payment\s*Date[:\s]*(\d{1,2}/\d{1,2}/\d{2,4})",
    "Total": r"Total\s*[:\s]*₹?([\d,]+)",
    "Currency": r"(?i)(?:Rs\.|₹|INR|USD|\$)"
}

@app.post("/process_pdf")
async def process_pdf(file: UploadFile = File(...)):
    # Define the absolute path to the temporary directory
    temp_dir = "/absolute/path/to/temp/"

    # Create the temporary directory if it doesn't exist
    os.makedirs(temp_dir, exist_ok=True)

    # Save uploaded PDF temporarily
    pdf_path = os.path.join(temp_dir, "temp.pdf")
    with open(pdf_path, "wb") as buffer:
        buffer.write(await file.read())

    # Extract text from PDF
    pdf_text = extract_text(pdf_path)

    # Extract tables from PDF
    pdf_tables = extract_tables(pdf_path)

    # Extract key information from text
    key_value_pairs = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, pdf_text)
        if match:
            if key == "Currency":
                if re.search(r"(?i)(Rs\.|₹|INR)", match.group(0)):
                    key_value_pairs[key] = "INR"
                elif re.search(r"(?i)(USD|\$)", match.group(0)):
                    key_value_pairs[key] = "USD"
            else:
                if key in ["To", "From"]:
                    # Concatenate multi-line addresses into a single line
                    key_value_pairs[key] = " ".join(match.group(1).split())
                else:
                    key_value_pairs[key] = match.group(1)

    # Save extracted tables to Excel files
    table_file_paths = save_tables_as_excel(pdf_tables)

    return JSONResponse(content={"key_value_pairs": key_value_pairs, "tables": table_file_paths})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)
