import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INVOICE = ROOT / "skills" / "moadian-invoice"
SEND = ROOT / "skills" / "moadian-send"
sys.path.insert(0, str(SEND / "scripts"))
sys.path.insert(0, str(INVOICE / "scripts"))
