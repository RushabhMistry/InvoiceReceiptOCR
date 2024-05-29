import tabula
import fitz  # PyMuPDF
import re
import pandas as pd
from fastapi import FastAPI, UploadFile, File
import uvicorn
import math
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow requests from any origin
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

class KeyValues(BaseModel):
    to: str
    from_: str
    transaction_id: str
    payment_mode: str
    payment_date: str
    total: str
    currency: str

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

# Function to convert data to JSON with special handling for float values
def json_safe(data):
    if isinstance(data, float):
        # Check for special float values
        if math.isinf(data) or math.isnan(data):
            return str(data)
        # Round float values to 2 decimal places
        return round(data, 2)
    elif isinstance(data, dict):
        return {key: json_safe(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [json_safe(item) for item in data]
    elif data is None:
        return None
    elif isinstance(data, str):
        return data
    elif isinstance(data, bool):
        return data
    elif isinstance(data, int):
        return data
    else:
        return str(data)

@app.post("/process_pdf/")
async def process_pdf(file: UploadFile = File(...)):
    # Save the uploaded PDF file
    with open("uploaded_pdf.pdf", "wb") as buffer:
        buffer.write(await file.read())
    
    # Extract text from PDF
    pdf_text = extract_text("uploaded_pdf.pdf")
    
    key_value_pairs = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, pdf_text)
        if match:
            if key == "Currency":
                if re.search(r"(?i)(Rs\.|₹|INR)", match.group(0)):
                    key_value_pairs[key.lower()] = "INR"
                elif re.search(r"(?i)(USD|\$)", match.group(0)):
                    key_value_pairs[key.lower()] = "USD"
            else:
                key_value_pairs[key.lower().replace(" ", "_")] = match.group(1)
    
    return JSONResponse(content=json_safe(key_value_pairs))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
