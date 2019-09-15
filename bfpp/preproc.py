import os


def preproc_file(filepath):
    lines = open(filepath).readlines()
    lines = [line.strip() for line in lines]

    result = ""
    for line in lines:
        if line.startswith("#include "):
            filename = line[len("#include "):]
            folder = os.path.dirname(filepath)
            inc_filepath = os.path.join(folder, filename)
            content = preproc_file(inc_filepath)
            result += content
        else:
            result = result + line + "\n"

    return result
