def remove_trailing_pipe(input_file, output_file):
    with open(input_file, 'r') as infile, open(output_file, 'w', newline='') as outfile:
        for line in infile:
            # Some lines are not properly read, need adjust for edge cases
            if line.endswith('|\n'):
                line = line[:-2] + '\n'
            elif line.endswith('|'):
                line = line[:-1] + '\n'
            outfile.write(line)

# Removes end '|' char for each csv, then saves each as 1{csv name}.csv
# I set the path for the csvs to be in the same dir as the script. just make sure theres no dupes b4 running the script.
from pathlib import Path

for csvs in Path("./").glob('*.csv'):
    remove_trailing_pipe(csvs, f'1{csvs}')