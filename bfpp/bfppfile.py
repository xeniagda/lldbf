def lpad(st, width):
    return " " * (width - len(st)) + st

class BFPPFile:
    def __init__(self, name, content):
        self.name = name

        self.lines = content.rstrip().split("\n")

        self.line_idxs = [0]

        total_len = 0
        for line in self.lines:
            total_len += len(line) + 1
            self.line_idxs.append(total_len)

    def line_offset_for_pos(self, pos):
        # Binary search over line_idxs
        start = -1 # Inclusive
        end = len(self.line_idxs) + 2 # Not inclusive

        while start != end - 1:
            mid = start + (end - start) // 2

            if mid < 0 or mid >= len(self.line_idxs):
                return mid
            if self.line_idxs[mid] <= pos:
                start = mid
            else:
                end = mid

        return (start, pos - self.line_idxs[start])

    def __str__(self):
        return "BFPPFile({}, {} lines)".format(
            self.name,
            len(self.line_idxs),
        )

    def __repr__(self):
        return "BFPPFile({})".format(self.name)

class Span:
    def __init__(self, bfile, start, end):
        self.bfile = bfile
        self.start = start
        self.end = end

    def show_ascii_art(self):
        # Shows a span in the following format:
        # filename.bf
        #     ,----------------V
        #     |  9 | row five. here the span is starting
        #     | 10 | the span continues
        #     | .. | ...
        #     | 12 | almost done!
        #     | 13 | the span ends here. no more span!
        #     `-----------------------^
        # Returns a list of lines
        #
        # TODO: Nicer one-line spans, in this format:
        # 57 | Here's a one line span: hello world! Now it's done
        #                              ^----------^

        start_line, start_offset = self.bfile.line_offset_for_pos(self.start)
        end_line, end_offset = self.bfile.line_offset_for_pos(self.end)

        lines = self.bfile.lines[start_line : end_line + 1]

        number_width = len(str(end_line + 1))
        l_space = number_width + 5

        indent = "    "

        first_line = "In file {}, lines {}..{}:".format(self.bfile.name, start_line + 1, end_line + 1)
        second_line = indent + "," + "-" * (l_space - 1 + start_offset) + "V"
        last_line = indent + "`" + "-" * (l_space - 1 + end_offset - 1) + "^"

        inbetween = []
        for line in range(start_line, end_line + 1):
            line_st = lpad(str(line + 1), number_width)
            inbetween.append(indent + "| {} | {}".format(line_st, self.bfile.lines[line]))

        if len(inbetween) > 5:
            inbetween = inbetween[:2] + [indent + "| ..."] + inbetween[-2:]

        return [first_line, second_line] + inbetween + [last_line]

    def __str__(self):
        start_line, start_offset = self.bfile.line_offset_for_pos(self.start)
        end_line, end_offset = self.bfile.line_offset_for_pos(self.end)

        return "{}@{}:{}..{}:{}".format(
            self.bfile.name,
            str(start_line + 1),
            str(start_offset),
            str(end_line + 2),
            str(end_offset)
        )

    def __repr__(self):
        return "Span(bile={},start={},end={})".fromat(
            self.bfile,
            self.start,
            self.end,
        )

if __name__ == "__main__":
    f = open("code/base10.bfpp").read()
    bf = BFPPFile("base10", f)

    import random

    print(bf.line_idxs)

    start = random.randrange(0, len(f))
    end = random.randrange(start + 1, len(f) + 1)

    span = Span(bf, start, end)

    print(f[start-5:start] + "*" + f[start] + "*" + f[start+1:start+6])
    print(f[end-5:end] + "*" + f[end] + "*" + f[end+1:end+6])
    print()

    print("\n".join(span.show_ascii_art()))
