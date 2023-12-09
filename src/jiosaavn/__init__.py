"Jiosaavn Downloader"
__version__ = "0.0.1"

from jiosaavn.utils import log, ic
from jiosaavn.main import JiosaavnDownload


log.info('Jiosaavn Module Initialized')

ic.disable()
#ic.enable()     # Comment this line out to enable debugger


if ic.enabled:
    log.setLevel(10) #debug
else:
    log.setLevel(20) #info

log.debug(f'Icecream Debugger: {ic.enabled}')