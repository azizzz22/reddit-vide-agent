"""
Caption Validator - Aligns SRT captions with original script using Gemini
"""

import os
import srt
from datetime import timedelta
import google.generativeai as genai
from typing import List, Tuple

class CaptionValidator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("models/gemini-flash-latest")
    
    def validate_and_correct(self, srt_path: str, original_script: str) -> str:
        """
        Validates SRT captions against original script and corrects mismatches.
        Returns path to corrected SRT file.
        """
        print("📝 Validating captions against script...")
        
        # 1. Parse existing SRT
        with open(srt_path, 'r', encoding='utf-8') as f:
            srt_content = f.read()
        
        subtitles = list(srt.parse(srt_content))
        
        # 2. Extract SRT text
        srt_text = " ".join([sub.content for sub in subtitles])
        
        # 3. Use Gemini to align
        corrected_text = self._align_with_gemini(srt_text, original_script)
        
        # 4. Rebuild SRT with corrected text
        corrected_srt = self._rebuild_srt(subtitles, corrected_text, original_script)
        
        # 5. Save corrected SRT
        output_path = srt_path.replace(".srt", "_validated.srt")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(corrected_srt)
        
        print(f"   ✅ Validated captions saved to: {os.path.basename(output_path)}")
        return output_path
    
    def _align_with_gemini(self, srt_text: str, script: str) -> str:
        """Use Gemini to correct SRT text based on script."""
        prompt = f"""
        Kamu adalah expert transcription validator. 
        
        SCRIPT ASLI (yang benar):
        {script}
        
        TRANSCRIPTION (dari Whisper, mungkin ada kesalahan):
        {srt_text}
        
        TUGAS:
        1. Bandingkan transcription dengan script asli
        2. Perbaiki kata-kata yang salah dalam transcription
        3. Pastikan nama brand, istilah teknis, dan kata kunci penting (seperti "Red Bull", "slackline", dll) PERSIS seperti di script
        4. Pertahankan timing/struktur kalimat dari transcription (jangan ubah urutan drastis)
        5. Output HANYA teks yang sudah diperbaiki, tanpa penjelasan
        
        Contoh koreksi:
        - Script: "Red Bull" → Transcription: "red ball" → PERBAIKI: "Red Bull"
        - Script: "1.6 mil" → Transcription: "satu koma enam mil" → PERBAIKI: "1.6 mil"
        - Script: "slackline" → Transcription: "slack line" → PERBAIKI: "slackline"
        
        Output format: Text yang sudah diperbaiki saja (plain text, no markdown).
        """
        
        try:
            response = self.model.generate_content(prompt)
            corrected = response.text.strip()
            
            # Remove markdown formatting if any
            corrected = corrected.replace('```', '').replace('**', '').strip()
            
            return corrected
        except Exception as e:
            print(f"   ⚠️ Gemini alignment error: {e}")
            return srt_text  # Return original if fails
    
    def _rebuild_srt(self, original_subs: List, corrected_text: str, original_script: str) -> str:
        """
        Rebuild SRT file with corrected text while preserving timing.
        """
        # Split corrected text into words
        corrected_words = corrected_text.split()
        
        # Calculate words per subtitle (average)
        total_subs = len(original_subs)
        words_per_sub = max(1, len(corrected_words) // total_subs)
        
        # Rebuild subtitles
        new_subtitles = []
        word_index = 0
        
        for i, original_sub in enumerate(original_subs):
            # Determine how many words for this subtitle
            if i == total_subs - 1:
                # Last subtitle gets remaining words
                sub_words = corrected_words[word_index:]
            else:
                # Try to match original word count
                original_word_count = len(original_sub.content.split())
                sub_words = corrected_words[word_index:word_index + original_word_count]
                word_index += original_word_count
            
            # Create new subtitle with corrected text but original timing
            new_sub = srt.Subtitle(
                index=original_sub.index,
                start=original_sub.start,
                end=original_sub.end,
                content=" ".join(sub_words) if sub_words else original_sub.content
            )
            new_subtitles.append(new_sub)
        
        return srt.compose(new_subtitles)
