from pathlib import Path
import ast

HOME=Path('src/home_v2.py'); SHELL=Path('src/orbidense_shell.py')

def main():
    assert HOME.exists() and SHELL.exists()
    ht=HOME.read_text(encoding='utf-8'); st=SHELL.read_text(encoding='utf-8')
    ast.parse(ht); ast.parse(st)
    assert 'ORBIDENSE AI' not in ht
    assert 'ORBIDENSE AI' not in st
    for route in ['Climate Outlook','Compare','Global Insights','Climate Action','About']:
        assert f"'{route}'" in ht or f'"{route}"' in ht
    for label in ['Home','Climate Outlook','Population Exposure','Climate Action','Compare','Global Insights','About']:
        assert f"'{label}'" in st or f'"{label}"' in st
    assert 'st.sidebar' not in ht and 'st.sidebar' not in st
    print('ORBIDENSE FINAL HOME STATIC BACKTEST: PASS')
    print('Public ORBIDENSE AI branding occurrences: 0')

if __name__=='__main__':
    main()
