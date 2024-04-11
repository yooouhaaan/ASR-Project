import csv

# Read labels.csv file
char_to_id = {}
with open('labels.csv', 'r', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    next(reader)  # Skip header
    for row in reader:
        char_to_id[row[1]] = int(row[0])

# Read transcript.txt and add a new column with text converted to ids
with open('transcripts.txt', 'r', encoding='utf-8') as infile, open('transcripts-final.txt', 'w', encoding='utf-8', newline='') as outfile:
    # Skip the first row of transcript.txt
    next(infile)

    # Manually specify the field names
    fieldnames = ['filename', 'text']  
    reader = csv.DictReader(infile, fieldnames=fieldnames, delimiter=',')  

    # Define new fieldnames and add 'text_ids'
    new_fieldnames = fieldnames + ['text_ids']
    writer = csv.DictWriter(outfile, fieldnames=new_fieldnames, delimiter=',')  
    writer.writeheader()

    for row in reader:
        text = row['text']
        if text:  # Check if text is not None or empty
            # Convert each character to its corresponding id
            ids = [str(char_to_id[char]) for char in text if char in char_to_id]
            # Create a string of converted ids separated by spaces
            converted_text_ids = '1 ' + ' '.join(ids) + ' 2'
            row['text_ids'] = converted_text_ids
            writer.writerow(row)

print("Conversion complete. Results saved in transcripts-final.txt")
