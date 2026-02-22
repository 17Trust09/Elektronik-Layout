# PyInstaller spec
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('.', includes=['assets/*', 'assets/**/*'])

block_cipher = None

a = Analysis(['app/main.py'], datas=datas, hiddenimports=['jinja2'], pathex=[])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, name='stromkreisdoku', console=False)
