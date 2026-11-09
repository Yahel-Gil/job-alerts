from . import amat, amazon, apple, intel, microsoft, nvidia, qualcomm

SOURCES = {m.NAME: m for m in (nvidia, intel, amat, apple, microsoft, amazon, qualcomm)}
