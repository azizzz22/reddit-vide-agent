import google.generativeai as genai
from typing import Dict, Any
from .base_agent import BaseAgent
from ..core.config import Config

class ScriptwriterAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Configure with a key initially, but we might need to re-configure per request if the library requires it.
        # The genai library sets a global api_key. To support rotation, we might need to pass `api_key` to `GenerativeModel` or re-configure.
        # `genai.configure` is global. 
        # Better approach: Configure with one key, but if we want true rotation per request, we'd re-configure.
        # For simplicity, let's pick one at init.
        self.api_key = Config.get_gemini_key()
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(Config.SCRIPT_MODEL)

    async def execute(self, post_data: Dict[str, Any]) -> str:
        """
        Generates a script from the Reddit post data.
        """
        print("ScriptwriterAgent: Generating script...")
        
        title = post_data.get("title", "Tanpa Judul")
        content = post_data.get("content", "")
        has_video = bool(post_data.get("video_path"))
        comments = post_data.get("comments_text", [])
        
        # Format comments for prompt
        comments_str = ""
        if comments:
            comments_str = "\nKOMENTAR NETIZEN TERATAS:\n"
            for c in comments:
                comments_str += f"- {c['author']}: {c['text'][:200]}...\n"
        
        # Validasi basic
        if not title and not content:
            print("⚠️ Warning: No title or content found for scripting.")
            return "Waduh, postingannya kosong nih! Tapi kayaknya seru banget deh. Coba cek langsung aja ya!"

        # Contextual Prompt Construction
        context_str = "Postingan ini berisi VIDEO." if has_video else "Postingan ini berupa TEKS/GAMBAR."
        
        prompt = f"""
        Kamu adalah expert scriptwriter untuk video viral TikTok/YouTube Shorts.
        
        Tugas: Buat naskah narasi yang engaging DENGAN VIDEO BREAK yang NATURAL.
        
        STRUKTUR WAJIB (4 BAGIAN):
        1. **Narration Part 1** (8-12 detik): Hook & build context
           - WAJIB mention "postingan Reddit" atau "konten Reddit" di awal
           - WAJIB reference screenshot dengan *<SHOW:screenshot_post>*
           - Contoh: "Waduh giiilaa! Gua nemu postingan Reddit yang kacau bener! *<SHOW:screenshot_post>* Judulnya '{title}' dan..."
        2. **[VIDEO_BREAK]** (10-15 detik): Dramatic pause dengan video clip
        3. **Narration Part 2** (8-12 detik): Deep dive atau punchline
           - Boleh reference komentar dengan *<SHOW:screenshot_comment_1>*
        4. **Narration Part 3** (5-8 detik): Closing hook
        
        CONTOH STRUKTUR:
        ```
        Waduh giiilaa! Gua nemu postingan Reddit yang kacau bener! *<SHOW:screenshot_post>* Ini tuh gua nemu kontennya gak sengaja dan langsung ternganga-nganga gua liatnya. Dari postingan yang berjudul "Float like a butterfly, sting like a bee" ada seorang bocil yang jago banget gerakan taktisnya...
        
        [VIDEO_BREAK: duration=12s, clip=action]
        
        Luar biasa kan? Kalian lihat gimana speed-nya? Itu bukan cuma asal pukul, ada teknik di sana. Float like a butterfly, sting like a bee! Netizen bilang ini future champion. Kalau suka konten inspiring kayak gini, jangan lupa like! *<SHOW:screenshot_comment_1>*
        
        Gimana menurut kalian? Komen di bawah ya!
        ```
        
        FORMAT VIDEO_BREAK:
        [VIDEO_BREAK: duration=10-15s, clip=action]
        
        Clip options:
        - action: Untuk momen aksi utama
        - punchline: Untuk momen lucu/mengejutkan  
        - intro: Untuk establishing shot
        
        ATTENTION CUE EXAMPLES:
        - "Coba kalian lihat ini!"
        - "Sekarang perhatikan baik-baik!"
        - "Ini dia momennya guys!"
        - "Liat deh gimana dia lakuin ini!"
        
        ATURAN:
        - Bahasa Indonesia casual & engaging
        - NO asterisks, brackets, formatting
        - Attention cue HARUS pendek (max 10 kata)
        - Part 1: Build anticipation
        - Part 2: React & explain
        
        CONTOH OUTPUT:
        ```
        Gila guys! Ada bocah umur 8 tahun yang bisa boxing kayak Muhammad Ali! Bayangin, gerakan tangannya cepet banget, footwork-nya juga udah pro level. Ini bukan main-main, dia latihan serius guys. Coba kalian lihat ini!
        
        [VIDEO_BREAK: duration=12s, clip=action]
        
        Luar biasa kan? Kalian lihat gimana speed-nya? Itu bukan cuma asal pukul, ada teknik di sana. Float like a butterfly, sting like a bee! Netizen bilang ini future champion. Kalau suka konten inspiring kayak gini, jangan lupa like!
        ```
        
        **PENTING - VISUAL MARKERS (Context-Aware):**
        Untuk membuat video lebih kontekstual, tambahkan 2 JENIS MARKERS:
        
        **A. SHOW MARKERS** (Untuk screenshot Reddit - WAJIB):
        - Format: *<SHOW:screenshot_id>*
        - screenshot_post: Screenshot postingan Reddit (WAJIB di opening)
        - screenshot_comment_N: Screenshot komentar (opsional, jika mention komentar)
        - Contoh: "...postingan Reddit yang kacau! *<SHOW:screenshot_post>* Judulnya..."
        - Contoh: "...netizen bilang *<SHOW:screenshot_comment_1>* 'ini bocil future champion'..."
        
        **B. VISUAL MARKERS** (Untuk objek/konsep - max 2-3):
        
        **1. FACTUAL MARKERS** (Objek/fakta yang PASTI ada di konten):
        - Objek yang disebutkan di judul/konten asli
        - Alat/benda yang jelas terlihat di video
        - Fakta yang tidak bisa dibantah
        - Format: *<VISUAL:factual|id|description>*
        - Narasi: LANGSUNG SHOW (positive framing)
        - Contoh: "...alat yang namanya boxing spinning bar *<VISUAL:factual|spinning_bar|boxing training spinning bar equipment>* yang biasa dipake..."
        
        **2. AMBIGUOUS MARKERS** (Asumsi/interpretasi yang BELUM TENTU benar):
        - Komentar netizen yang spekulatif
        - Interpretasi visual yang tidak pasti dari data
        - Humor/sarkasme/opini
        - Format: *<VISUAL:ambiguous|id|description>*
        - Narasi: NEGATIF TRUE (manage expectation)
        - Contoh: "...fokus ke rambutnya yang ikonik, untungnya *<VISUAL:ambiguous|mohawk|gangster mohawk hairstyle>* gak kaya gengster beneran"
        
        **RULES:**
        - WAJIB: Min 1 SHOW marker (screenshot_post)
        - OPSIONAL: Max 2-3 VISUAL markers
        - Prioritaskan FACTUAL markers
        - Gunakan AMBIGUOUS hanya untuk humor/spekulasi
        - Pastikan narasi flow natural

        
        DATA KONTEN:
        Judul: {title}
        Selftext: {content}
        
        Komentar Top:
        {comments_str}
        
        Generate script dengan struktur 4 bagian + visual markers (factual/ambiguous). Output HANYA script (no explanation).
        """
        
        try:
            response = self.model.generate_content(prompt)
            script = response.text.strip()
            
            # Cleanup extra formatting if Gemini adds it despite instructions
            script = script.replace("Narrator:", "").replace("Voiceover:", "").strip()
            
            # PRESERVE [VIDEO_BREAK] markers but remove other brackets
            import re
            
            # Temporarily replace VIDEO_BREAK markers with placeholder
            video_breaks = re.findall(r'\[VIDEO_BREAK:.*?\]', script)
            for i, vb in enumerate(video_breaks):
                script = script.replace(vb, f"<<<VIDEO_BREAK_{i}>>>")
            
            # Now remove other brackets/parentheses
            script = re.sub(r'\[.*?\]', '', script)
            script = re.sub(r'\(.*?\)', '', script)
            
            # Remove asterisks (often used for *actions* or *emphasis*)
            script = re.sub(r'\*.*?\*', '', script)  # Remove content inside asterisks
            script = script.replace('*', '')  # Remove standalone asterisks
            
            # Restore VIDEO_BREAK markers
            for i, vb in enumerate(video_breaks):
                script = script.replace(f"<<<VIDEO_BREAK_{i}>>>", vb)
            
            # Remove markdown code blocks if present
            script = script.replace('```', '')
            
            # Clean up whitespace
            script = ' '.join(script.split())
            
            # Extract visual markers
            visual_markers = self._extract_visual_markers(script)
            
            return {
                "script": script,
                "visual_markers": visual_markers
            }
            
        except Exception as e:
            print(f"Error generating script: {e}")
            return {
                "script": "Halo guys! Ini konten menarik dari Reddit. Jangan lupa like dan subscribe!",
                "visual_markers": []
            }
    
    def _extract_visual_markers(self, script: str) -> list:
        """Extract visual markers (SHOW + VISUAL) with certainty classification from script."""
        import re
        markers = []
        
        # Pattern 1: SHOW markers (screenshots) - *<SHOW:screenshot_id>*
        show_pattern = r'\*<SHOW:([^>]+)>\*'
        show_matches = re.findall(show_pattern, script)
        
        for screenshot_id in show_matches:
            markers.append({
                "id": screenshot_id.strip(),
                "type": "screenshot",
                "certainty": "factual",  # Screenshots are always factual
                "description": f"Reddit {screenshot_id.replace('_', ' ')}"
            })
        
        # Pattern 2: VISUAL markers - *<VISUAL:certainty|id|description>*
        visual_pattern = r'\*<VISUAL:([^|>]+)\|([^|>]+)\|([^>]+)>\*'
        visual_matches = re.findall(visual_pattern, script)
        
        for certainty, marker_id, description in visual_matches:
            certainty = certainty.strip().lower()
            
            # Validate certainty
            if certainty not in ["factual", "ambiguous"]:
                print(f"   ⚠️ Invalid certainty '{certainty}' for marker '{marker_id}', defaulting to 'factual'")
                certainty = "factual"
            
            markers.append({
                "id": marker_id.strip(),
                "type": "visual",
                "certainty": certainty,
                "description": description.strip()
            })
        
        # Log classification stats
        screenshot_count = sum(1 for m in markers if m["type"] == "screenshot")
        factual_count = sum(1 for m in markers if m["type"] == "visual" and m["certainty"] == "factual")
        ambiguous_count = sum(1 for m in markers if m["type"] == "visual" and m["certainty"] == "ambiguous")
        
        print(f"   ✅ Extracted {len(markers)} markers ({screenshot_count} screenshots, {factual_count} factual, {ambiguous_count} ambiguous)")
        
        return markers
