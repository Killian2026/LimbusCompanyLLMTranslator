"""
LCLT (Limbus Company Localization Tool) 运行脚本
"""

from src.main import LCLT

if __name__ == "__main__":
    lclt = LCLT()
    lclt.update()
    
    # 等待用户按下按键后关闭窗口
    input()