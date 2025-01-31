import streamlit as st
import os
import base64
import yt_dlp
from openai import OpenAI
import subprocess
import PyPDF2
from docx import Document
import pandas as pd
import requests
from bs4 import BeautifulSoup  # For web scraping

# Initialize Groq client
groq = OpenAI(
    api_key="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",
    base_url="https://api.groq.com/openai/v1"
)

# Configuration
MAX_FILE_SIZE_MB = 50
SUPPORTED_TYPES = ["mp3", "wav", "mp4", "mov", "avi", "mkv", "pdf", "docx", "csv", "xlsx"]

# Session state initialization
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "transcript" not in st.session_state:
    st.session_state.transcript = ""
if "current_file" not in st.session_state:  # Track the currently uploaded file
    st.session_state.current_file = None

# Helper Functions
def optimize_audio(input_path, output_path="temp_audio.ogg"):
    """Convert any audio/video to optimized format"""
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path,
            "-vn", "-ac", "1", "-c:a", "libopus",
            "-b:a", "12k", "-application", "voip",
            "-threads", "4", output_path
        ], check=True)
        return output_path
    except Exception as e:
        st.error(f"Audio optimization failed: {e}")
        return None

def groq_transcribe(file_path):
    """Fast transcription using Whisper"""
    try:
        with open(file_path, "rb") as f:
            response = groq.audio.transcriptions.create(
                model="whisper-large-v3",
                file=f,
                response_format="text"
            )
        return response
    except Exception as e:
        st.error(f"Transcription failed: {e}")
        return None

def groq_chat(prompt, history):
    """Interactive chat with memory"""
    try:
        messages = [{"role": "system", "content": "You're a helpful assistant. Keep responses concise and accurate."}]
        messages += history
        messages.append({"role": "user", "content": prompt})
        
        response = groq.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Chat failed: {e}")
        return None

def preprocess_content(content):
    """Preprocess content to remove duplicates and irrelevant parts"""
    lines = content.split("\n")
    unique_lines = []
    seen = set()
    for line in lines:
        stripped_line = line.strip()
        if stripped_line and stripped_line not in seen:
            unique_lines.append(stripped_line)
            seen.add(stripped_line)
    return "\n".join(unique_lines)

def split_into_chunks(text, max_tokens=4000):
    """Split text into chunks of max_tokens"""
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 <= max_tokens:
            current_chunk.append(word)
            current_length += len(word) + 1
        else:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = len(word) + 1
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks

def extract_text_from_website(url):
    """Scrape text content from a website"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(separator="\n")
        return text
    except Exception as e:
        st.error(f"Website content extraction failed: {e}")
        return None

def download_youtube(url):
    """Download YouTube audio quickly"""
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'yt_audio.%(ext)s',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
            'quiet': True,
            'noprogress': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info).replace(".webm", ".mp3")
    except Exception as e:
        st.error(f"YouTube download failed: {e}")
        return None

# Streamlit UI
st.set_page_config(page_title="🤖 AI Assistant Pro", layout="wide")
st.markdown("""
    <style>
    .main { padding: 2rem; }
    .stButton>button { border-radius: 10px; transition: 0.3s; }
    .stButton>button:hover { transform: scale(1.05); }
    .chat-message { padding: 1rem; border-radius: 10px; margin: 1rem 0; }
    </style>
    """, unsafe_allow_html=True)
st.title("🤖 AI Assistant Pro")

# Main tabs
tab1, tab2 = st.tabs(["📄 File Upload", "🔗 Link Input"])

with tab1:
    st.header("File Upload, Transcription, and AI Chat")

    # File upload
    uploaded_file = st.file_uploader("Upload a file", type=SUPPORTED_TYPES)

    # Reset session state if a new file is uploaded
    if uploaded_file:
        if uploaded_file.name != st.session_state.current_file:
            st.session_state.chat_history = []  # Clear chat history
            st.session_state.transcript = ""    # Clear transcript
            st.session_state.current_file = uploaded_file.name  # Update current file name

        if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
            st.error(f"File size exceeds {MAX_FILE_SIZE_MB}MB limit")
        else:
            file_path = f"uploaded_{uploaded_file.name}"
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Extract text based on file type
            if uploaded_file.type == "application/pdf":
                st.info("Extracting text from PDF...")
                transcript = extract_text_from_pdf(file_path)
            elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                st.info("Extracting text from Word document...")
                transcript = extract_text_from_docx(file_path)
            elif uploaded_file.type == "text/csv":
                st.info("Extracting text from CSV...")
                transcript = extract_text_from_csv(file_path)
            elif uploaded_file.type in ["application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
                st.info("Extracting text from Excel...")
                transcript = extract_text_from_excel(file_path)
            elif uploaded_file.type.startswith("audio/") or uploaded_file.type.startswith("video/"):
                st.info("Optimizing audio/video for transcription...")
                optimized_path = optimize_audio(file_path)
                if optimized_path:
                    st.info("Transcribing audio...")
                    transcript = groq_transcribe(optimized_path)
                    os.remove(optimized_path)
            else:
                st.error("Unsupported file type.")
                transcript = None
            
            if transcript:
                # Preprocess content
                transcript = preprocess_content(transcript)
                st.session_state.transcript = transcript
                st.subheader("📝 Extracted Content")
                st.write(transcript)

with tab2:
    st.header("Link Input, Transcription, and AI Chat")

    # Link input
    link = st.text_input("Enter a YouTube or Website URL")
    if link:
        if "youtube.com" in link:
            st.info("Downloading YouTube audio...")
            file_path = download_youtube(link)
            if file_path:
                st.info("Optimizing audio for transcription...")
                optimized_path = optimize_audio(file_path)
                if optimized_path:
                    st.info("Transcribing audio...")
                    transcript = groq_transcribe(optimized_path)
                    os.remove(optimized_path)
                    os.remove(file_path)
        else:
            st.info("Extracting text from website...")
            transcript = extract_text_from_website(link)
        
        if transcript:
            # Preprocess content
            transcript = preprocess_content(transcript)
            st.session_state.transcript = transcript
            st.subheader("📝 Extracted Content")
            st.write(transcript)

# Chat interface (shared across both tabs)
st.subheader("💬 Ask Questions About the Content")
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Ask me anything..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # Add transcript to chat context
    full_context = (
        f"Context:\n{st.session_state.transcript}\n\nQuestion: {prompt}"
    )
    
    # Split content into chunks if too large
    chunks = split_into_chunks(full_context, max_tokens=4000)
    responses = []
    for chunk in chunks:
        with st.spinner("Thinking..."):
            try:
                response = groq_chat(chunk, st.session_state.chat_history)
                responses.append(response)
            except Exception as e:
                st.error(f"Chat error: {str(e)}")
    
    # Combine responses
    final_response = "\n".join(responses)
    st.session_state.chat_history.append({"role": "assistant", "content": final_response})
    with st.chat_message("assistant"):
        st.write(final_response)

# Cleanup temporary files
if os.path.exists("uploaded_file"):
    os.remove("uploaded_file")
if os.path.exists("temp_audio.ogg"):
    os.remove("temp_audio.ogg")