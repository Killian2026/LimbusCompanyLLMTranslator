"""
LCLT (Limbus Company Localization Tool) 运行脚本
"""

from src.main import LCLT

if __name__ == "__main__":
    lclt = LCLT()
    lclt.update(log=True)