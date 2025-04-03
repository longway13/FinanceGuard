"""
Configuration settings for the application
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI API settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "1.0"))

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

# Dataset paths
CASE_DB_PATH = os.path.join(DATASETS_DIR, "case_db.json")
EMBEDDING_PATH = os.path.join(DATASETS_DIR, "precomputed_embeddings.npz")

# Prompt paths
SIMULATION_PROMPT_PATH = os.path.join(PROMPTS_DIR, "simulate_dispute.txt")
FORMAT_PROMPT_PATH = os.path.join(PROMPTS_DIR, "format_output.txt")
HIGHLIGHT_PROMPT_PATH = os.path.join(PROMPTS_DIR, "highlight_prompt.txt")

# Ensure directories exist
for directory in [DATASETS_DIR, PROMPTS_DIR, UPLOADS_DIR]:
    os.makedirs(directory, exist_ok=True)
