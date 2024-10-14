# TODO: Add copyright/license notice

# ================================================== Libraries =========================================================

# =============================================== Various utilities ====================================================

class Text:
    INFO = f"\033[38;2;{0};{255};{150}m{'[INFO]:'}\033[0m"
    ERROR = f"\033[38;2;{220};{0};{0}m{'[ERROR]:'}\033[0m"
    DEBUG = f"\033[38;2;{0};{100};{255}m{'[DEBUG]:'}\033[0m"
    SPICE_PARSER = f"\033[38;2;{0};{160};{140}m{'|SPICE_PARSER|'}\033[0m"
    MAGIC_PARSER = f"\033[38;2;{0};{120};{200}m{'|MAGIC_PARSER|'}\033[0m"
    LAYOUT_CREATOR = f"\033[38;2;{232};{232};{24}m{'|LAYOUT_CREATOR|'}\033[0m"
    JSON_CONVERTER = f"\033[38;2;{136};{39};{220}m{'|JSON_CONVERTER|'}\033[0m"
