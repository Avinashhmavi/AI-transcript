import streamlit as st
import os
import base64
import yt_dlp
from openai import OpenAI
import subprocess

# Initialize Groq client
groq = OpenAI(
    api_key="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",
    base_url="https://api.groq.com/openai/v1"
)

# Fast audio processing functions
def audio_to_base64(file):
    """Quick audio to base64 conversion"""
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode()

def optimize_audio(input_path, output_path="optimized_audio.ogg"):
    """Fast parallel audio processing with FFmpeg"""
    subprocess.run([
        "ffmpeg", "-y", "-i", input_path,
        "-vn", "-ac", "1", "-c:a", "libopus",
        "-b:a", "12k", "-application", "voip",
        "-threads", "4", output_path
    ], check=True)

def download_youtube_audio(url):
    """High-speed YouTube audio download"""
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'yt_audio.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
        'quiet': True,
        'noprogress': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.download([url])

# Streamlit UI Configuration
st.set_page_config(page_title="⚡ Groq Turbo Transcriber", layout="wide")

st.markdown("""
    <style>
    .main { padding: 2rem; }
    .stButton>button { background: #4CAF50; color: white; border-radius: 8px; }
    audio { width: 100%; margin: 1rem 0; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Groq Turbo Transcriber")

def process_audio(audio_path):
    """Fast-track audio processing pipeline"""
    optimize_audio(audio_path)
    return audio_to_base64("optimized_audio.ogg")

def groq_transcribe(audio_path):
    """Ultra-fast transcription using Groq's Whisper"""
    with open(audio_path, "rb") as f:
        return groq.audio.transcriptions.create(
            model="whisper-large-v3",
            file=f,
            response_format="text",
            temperature=0.2  # For more accurate results
        )

def groq_summarize(text):
    """Quick summary with Llama3-70b"""
    return groq.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{
            "role": "user",
            "content": f"Summarize this in 3 bullet points:\n{text}"
        }],
        temperature=0.3,
        max_tokens=150
    ).choices[0].message.content

# Main Application Tabs
tab_upload, tab_youtube = st.tabs(["📤 File Upload", "🎥 YouTube"])

with tab_upload:
    uploaded_file = st.file_uploader("Upload MP3", type=["mp3"])
    if uploaded_file and st.button("🚀 Process File"):
        with st.spinner("⚡ Turbo Processing..."):
            # Save and process audio
            with open("upload.mp3", "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Show processed audio
            audio_b64 = process_audio("upload.mp3")
            st.audio(f"data:audio/ogg;base64,{audio_b64}")
            
            # Transcription
            transcript = groq_transcribe("optimized_audio.ogg")
            st.subheader("📝 Transcription")
            st.write(transcript)
            
            # Summary
            st.subheader("🔍 AI Summary")
            st.write(groq_summarize(transcript))

with tab_youtube:
    yt_url = st.text_input("YouTube URL")
    if yt_url and st.button("🚀 Process YouTube"):
        with st.spinner("⚡ Turbo Downloading..."):
            download_youtube_audio(yt_url)
            
            # Process audio
            audio_b64 = process_audio("yt_audio.mp3")
            st.audio(f"data:audio/ogg;base64,{audio_b64}")
            
            # Transcription
            transcript = groq_transcribe("optimized_audio.ogg")
            st.subheader("📝 Transcription")
            st.write(transcript)
            
            # Summary
            st.subheader("🔍 AI Summary")
            st.write(groq_summarize(transcript))