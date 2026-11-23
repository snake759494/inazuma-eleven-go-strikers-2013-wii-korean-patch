# 재빌드

## 준비물

- Python 3.11 이상, `pip install pillow pyelftools capstone`
- Git for Windows의 bash
- Dolphin의 `DolphinTool.exe`, [Wiimms ISO Tools](https://wit.wiimm.de/)의 `wit.exe` (`tools/wit/`에 둡니다)
- 원본 일본판 S5SJHF 디스크(RVZ 또는 ISO). ISO로 바꿨을 때 MD5가 README 표의 값이어야 합니다.
- 글꼴(`docs/FONT_CREDITS.md`)
- (동영상을 다시 만들 때) mobipeg `ffmpeg.exe` (x264 포크 링크, `docs/TECHNICAL.md` 참고)
- (배포 파일을 만들 때) xdelta3

## 순서

저장소 최상위에서 실행합니다. 작업 폴더는 `work/`입니다.

```bash
DolphinTool.exe convert -i 'Inazuma Eleven Go - Strikers 2013 (Japan).rvz' -o work/original.iso -f iso
cd work && ../tools/wit/wit.exe extract original.iso witx --psel=DATA && cd ..
mkdir -p work/orig && cp work/witx/files/{dat.bin,ui.bin,grp.bin,strap.bin,mcb0.bln,mcb1.bln} work/witx/sys/main.dol work/orig/
```

원문 목록을 디스크에서 뽑습니다(일본어 원문은 저장소에 넣지 않았으므로 직접 만듭니다).

```bash
python tools/py/extract.py      # work/dat/*.bin 이 필요 (dat.bin 각 항목을 풀어 둔 것)
python tools/py/prep.py         # work/text/in/*.json (번호는 text/tr/*.json과 대응)
cp text/tr/*.json work/text/out/
```

그림 글자와 글꼴을 만들고 빌드합니다.

```bash
python tools/py/shtx.py work/orig/ui.bin work/tex/ui   # 원본 텍스처 풀기
python tools/py/texedit.py                            # tex/spec_*.json 적용
python tools/py/mkcut.py && python tools/py/mknames.py && python tools/py/mkvert.py
python tools/py/mkmenu.py
python tools/py/build2.py                             # work/patch/files, work/patch_sys 생성
cd work
../tools/wit/wit.exe copy original.iso dec.iso --enc decrypt --psel whole
python ../tools/py/inject.py dec.iso
python ../tools/py/inject.py rehash dec.iso
../tools/wit/wit.exe copy dec.iso 'Inazuma Eleven Go - Strikers 2013 (Korean).iso' --enc encrypt --psel whole
python ../tools/py/inject.py restore dec.iso 'Inazuma Eleven Go - Strikers 2013 (Korean).iso' original.iso
python ../tools/py/inject.py fixtmd 'Inazuma Eleven Go - Strikers 2013 (Korean).iso'
../tools/wit/wit.exe verify 'Inazuma Eleven Go - Strikers 2013 (Korean).iso'
```

`wit verify`에서 `TMD is fake signed`, `+OK`가 나와야 합니다.

## 배포 파일 만들기

```bash
xdelta3 -e -0 -S none -A -B 2147483648 -s work/original.iso 'work/Inazuma Eleven Go - Strikers 2013 (Korean).iso' IE_GO_Strikers_2013_Wii_KO_v1.0.xdelta
```

결과 ISO의 SHA-256이 README 표의 값과 같으면 배포판과 같은 결과입니다.
