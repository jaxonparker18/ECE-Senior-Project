# CONSTS RGB
ORANGE_THEME_RGB = "rgb(255, 116, 24)"
WHITE_RGB = "rgb(255, 255, 255)"

# CONST WIDGETS
MAIN = ""   # border: 2px solid orange;

STATUS_BAR = f"background-color: {ORANGE_THEME_RGB};" \
             f"border: 1px solid black;"

TOP_BAR = f"background-color: {ORANGE_THEME_RGB};"

IP_ENTRY = f"background-color: {WHITE_RGB};" \
           "border: 2px solid black;"

PORT_ENTRY = f"background-color: {WHITE_RGB};" \
             "border: 2px solid black;"

CONNECT_BUTTON = "QPushButton {"\
                    "background-color: rgb(50, 50, 50); "\
                    "color: rgb(255, 255, 255);"\
                 "}"\
                 "QPushButton::pressed {"\
                    "background-color: rgb(100, 100, 100);"\
                 "}" \
                 "QPushButton:hover:!pressed"\
                 "{"\
                 "background-color: rgb(60, 60, 60);"\
                 "}"

STATUS_LABEL_DISCONNECTED = "color: red;"
STATUS_LABEL_CONNECTED = "color: green;"

LINE_SEPARATOR = "border: 3px solid black;"

FEED_LABEL = f"background-color: {ORANGE_THEME_RGB}; " \
             # "border: 3px solid red;"

