import os
import pandas as pd
from glob import glob

# directory of audio files
wav_directory = "your_audio_dataset_path_here"
# directory of text files
txt_directory = "your_transcript_dataset_path_here"

# get lists of wav files and text files
wav_files = glob(os.path.join(wav_directory, "*.wav"))
txt_files = glob(os.path.join(txt_directory, "*.txt"))

# make dataframe with lists above
data = []
for wav_file in wav_files:
    wav_basename = os.path.basename(wav_file)
    txt_file = os.path.join(txt_directory, os.path.splitext(wav_basename)[0] + ".txt")
    
    if txt_file in txt_files:
        with open(txt_file, 'r') as txt:
            script = txt.read()
            data.append({'filename': wav_file, 'text': script})

df = pd.DataFrame(data)

# save TXT file 
txt_path = "transcripts.txt"
df.to_csv(txt_path, sep=',', index=False, header=True)

print(f"transcripts.txt file saved.")
