from fastapi import FastAPI
from pipeline import run_fact_checking_pipeline

app = FastAPI()

@app.post("/verify")
async def verify_claim(text: str):
    return run_fact_checking_pipeline(text)