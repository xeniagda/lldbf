from bfpp_types import Byte, Struct

INIT_TYPES = {}

INIT_TYPES["Byte"] = Byte()

INIT_TYPES["ChPair"] = Struct([
    ("ch1", "Byte"),
    ("ch2", "Byte"),
])

INIT_TYPES["LChPair"] = Struct([
    ("ch_pair", "ChPair"),
    ("marker", "Byte")
])
