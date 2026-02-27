"""
Subtitle Service for handling SRT file operations and diarization
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional


class SubtitleService:
    """
    Service class to handle subtitle operations including SRT parsing, 
    diarization application, and format conversions
    """
    
    def __init__(self):
        pass
    
    def apply_diarization_to_srt(self, srt_path: Path, diarization_data: List[Dict], output_path: Path) -> bool:
        """
        Apply diarization data to an SRT file, adding speaker tags
        """
        try:
            with open(srt_path, "r", encoding="utf-8") as f:
                srt_content = f.read()
            
            # Split into subtitle blocks
            blocks = re.split(r'\n\s*\n', srt_content.strip())
            new_blocks = []
            
            for block in blocks:
                lines = block.split('\n')
                if len(lines) >= 3:
                    # Find timestamp line
                    time_match = re.search(r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})', lines[1])
                    if time_match:
                        # Simple time to milliseconds converter
                        def to_ms(t: str) -> float:
                            parts = re.split('[:.,]', t)
                            h, m, s, ms = map(int, parts)
                            return (h * 3600 + m * 60 + s) * 1000 + ms
                        
                        start_ms = to_ms(time_match.group(1))
                        end_ms = to_ms(time_match.group(2))
                        mid_s = (start_ms + end_ms) / 2 / 1000
                        
                        # Find the speaker for this time segment
                        speaker_id = 0
                        for d_seg in diarization_data:
                            if d_seg['start'] <= mid_s <= d_seg['end']:
                                speaker_id = d_seg['speaker']
                                break
                        
                        # Add speaker tag to the text line
                        lines[2] = f"[S{speaker_id}] {lines[2]}"
                        new_blocks.append('\n'.join(lines))
                    else:
                        new_blocks.append(block)
                else:
                    new_blocks.append(block)
            
            # Write the modified SRT
            with open(output_path, "w", encoding="utf-8") as f:
                f.write('\n\n'.join(new_blocks))
            
            return True
        except Exception:
            return False
    
    def parse_srt_content(self, srt_content: str) -> List[Dict]:
        """
        Parse SRT content into structured data
        """
        blocks = re.split(r'\n\s*\n', srt_content.strip())
        subtitles = []
        
        for i, block in enumerate(blocks):
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            if len(lines) >= 3:
                # Extract index, timing, and text
                idx = int(lines[0]) if lines[0].isdigit() else i+1
                
                # Extract timing
                time_match = re.search(r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})', lines[1])
                if time_match:
                    start_time = time_match.group(1)
                    end_time = time_match.group(2)
                    
                    # Join remaining lines as text
                    text = '\n'.join(lines[2:])
                    
                    subtitles.append({
                        'index': idx,
                        'start': start_time,
                        'end': end_time,
                        'text': text
                    })
        
        return subtitles
    
    def write_srt_file(self, subtitles: List[Dict], output_path: Path) -> bool:
        """
        Write structured subtitle data to an SRT file
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, sub in enumerate(subtitles):
                    f.write(f"{i+1}\n")
                    f.write(f"{sub['start']} --> {sub['end']}\n")
                    f.write(f"{sub['text']}\n")
                    f.write("\n")
            return True
        except Exception:
            return False