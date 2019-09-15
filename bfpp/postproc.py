def postproc(code):
    while True:
        l = len(code)
        code = code.replace("+-", "")
        code = code.replace("-+", "")
        code = code.replace("<>", "")
        code = code.replace("><", "")
        if l == len(code):
            return code
