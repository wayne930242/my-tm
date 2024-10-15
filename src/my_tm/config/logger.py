from logging import getLogger
from logging import StreamHandler
from colorlog import ColoredFormatter
from logging import DEBUG, INFO

logger = getLogger(__name__)
logger.setLevel(INFO)

handler = StreamHandler()
handler.setLevel(INFO)

formatter = ColoredFormatter(
    # %(asctime)s [ %(log_color)s%(levelname)s%(reset)s ] %(message)s : %(filename)s:%(lineno)d
    "%(asctime)s [ %(log_color)s%(levelname)s%(reset)s ] %(message)s",
    datefmt="%H:%M:%S",
    reset=True,
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'blue',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    },
    secondary_log_colors={},
    style='%'
)
handler.setFormatter(formatter)

logger.addHandler(handler)
