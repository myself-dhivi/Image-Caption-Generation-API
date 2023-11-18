from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import io
import json
import requests
import pytesseract
from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer
import torch
from PIL import Image
import os
print("System PATH:", os.environ['PATH'])


model = VisionEncoderDecoderModel.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
feature_extractor = ViTImageProcessor.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
tokenizer = AutoTokenizer.from_pretrained("nlpconnect/vit-gpt2-image-captioning")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

max_length = 16
num_beams = 4
gen_kwargs = {"max_length": max_length, "num_beams": num_beams}

def predict_step(image_paths):
  images = []
  for image_path in image_paths:
    i_image = image_path
    if i_image.mode != "RGB":
      i_image = i_image.convert(mode="RGB")

    images.append(i_image)

  pixel_values = feature_extractor(images=images, return_tensors="pt").pixel_values
  pixel_values = pixel_values.to(device)

  output_ids = model.generate(pixel_values, **gen_kwargs)

  preds = tokenizer.batch_decode(output_ids, skip_special_tokens=True)
  preds = [pred.strip() for pred in preds]
  return preds

app = FastAPI(title="Image Captioning API", description="An API for generating caption for image.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ImageCaption(BaseModel):
    caption: str

@app.post("/predict/", response_model=ImageCaption)
def predict(file: UploadFile = File(...)):
    # Load the image file into memory
    contents = file.file.read()
    image = Image.open(io.BytesIO(contents))
    result = predict_step([image])
    return JSONResponse(content={"caption": result})

# Text Extraction API
@app.post("/extract_text/", response_model=dict)
def extract_text(file: UploadFile = File(...)):
    contents = file.file.read()
    image = Image.open(io.BytesIO(contents))

    # Check if the image mode is not RGB and convert it
    if image.mode != "RGB":
        image = image.convert(mode="RGB")

    # Use pytesseract to extract text from the image
    extracted_text = pytesseract.image_to_string(image)

    # Check if the extracted text is empty or contains only whitespace
    cleaned_text = extracted_text.strip()
    if not cleaned_text:
        return JSONResponse(content={"message": "No text found in the image"})

    return JSONResponse(content={"extracted_text": cleaned_text})

# Redirect the user to the documentation
@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse(url="/docs")



