import os


def remove_trailing_pipe_from_csv(input_file, output_file):
    with open(input_file, "r") as infile, open(output_file, "w") as outfile:
        for line in infile:
            outfile.write(line.rstrip("|") + "\n")


def convert_pipes_to_commas(input_file, output_file):
    with open(input_file, "r") as infile, open(output_file, "w") as outfile:
        for line in infile:
            outfile.write(line.replace("|", ","))


def process_csv_files_in_directory(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".csv"):
                input_file = os.path.join(root, file)
                temp_file = os.path.join(root, f"temp_{file}")
                output_file = os.path.join(root, f"processed_{file}")

                # First, remove trailing pipes
                remove_trailing_pipe_from_csv(input_file, temp_file)

                # Then, convert pipes to commas
                convert_pipes_to_commas(temp_file, output_file)

                # Remove the temporary file
                os.remove(temp_file)

                print(f"Processed {input_file} -> {output_file}")


process_csv_files_in_directory("data")
