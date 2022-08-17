# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files
from numpy import loadtxt
import shutil

# fix hidden imports
hidden_imports = loadtxt("requirements.txt", comments="#", delimiter=",", unpack=False, dtype=str, encoding="utf-8")
hidden_imports = [x.split("=")[0] for x in hidden_imports] + ["dicom_anonymizer"]
hidden_imports = [x.lower() for x in hidden_imports]

shutil.copytree("./images/", "./tmp_dependencies/images/")

a = Analysis(['./main.py'],
             pathex=['.'],
             binaries=[],
             datas=[],
             hiddenimports=hidden_imports,
             hookspath=["./hooks/"],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=None,
             noarchive=False
)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=None
)

# to compile everything into a macOS Bundle (.APP)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='DICOMAnonymizer',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True,
          #icon="./tmp_dependencies/images/dicomanonymizer-logo.ico"
)
coll = COLLECT(exe,
               a.binaries,
               Tree("./tmp_dependencies/"),
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='DICOMAnonymizer'
)