import csv
from collections import Counter

input_file = 'transcripts.txt'
output_file = 'labels.csv'

# extract text from transcripts.txt file
texts = []
with open(input_file, 'r', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        texts.append(row['text'])

# count frequency of the characters
all_text = ''.join(texts)
char_counts = Counter(all_text)

# sort characters by the frequency
sorted_chars = sorted(char_counts.items(), key=lambda x: x[1], reverse=True)

# make labels.csv file
with open(output_file, 'w', encoding='utf-8', newline='') as csvfile:
    fieldnames = ['id', 'char', 'freq']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    # add <pad>, <sos>, and <eos> tokens
    writer.writerow({'id': 0, 'char': '<pad>', 'freq': 0})
    writer.writerow({'id': 1, 'char': '<sos>', 'freq': 0})
    writer.writerow({'id': 2, 'char': '<eos>', 'freq': 0})

    for idx, (char, freq) in enumerate(sorted_chars, start=3):
        writer.writerow({'id': idx, 'char': char, 'freq': freq})

print("labels.csv file saved.")
