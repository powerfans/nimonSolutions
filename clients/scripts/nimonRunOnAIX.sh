#!/bin/sh
skip=44

tab='	'
nl='
'
IFS=" $tab$nl"

umask=`umask`
umask 77

gztmpdir=
trap 'res=$?
  test -n "$gztmpdir" && rm -fr "$gztmpdir"
  (exit $res); exit $res
' 0 1 2 3 5 10 13 15

if type mktemp >/dev/null 2>&1; then
  gztmpdir=`mktemp -dt`
else
  gztmpdir=/tmp/gztmp$$; mkdir $gztmpdir
fi || { (exit 127); exit 127; }

gztmp=$gztmpdir/$0
case $0 in
-* | */*'
') mkdir -p "$gztmp" && rm -r "$gztmp";;
*/*) gztmp=$gztmpdir/`basename "$0"`;;
esac || { (exit 127); exit 127; }

case `echo X | tail -n +1 2>/dev/null` in
X) tail_n=-n;;
*) tail_n=;;
esac
if tail $tail_n +$skip <"$0" | gzip -cd > "$gztmp"; then
  umask $umask
  chmod 700 "$gztmp"
  (sleep 5; rm -fr "$gztmpdir") 2>/dev/null &
  "$gztmp" ${1+"$@"}; res=$?
else
  echo >&2 "Cannot decompress $0"
  (exit 127); res=127
fi; exit $res
��I�`nimonRunOnAIX.sh ��Ao�0���S�/��ɜ;p�8������(�Z҂���}q+�j/����K��q5�YK��D�ԁ��Ay-�a�ES&��Y*E���وo�J�݆��LU#P�R
�"e�D"/�6|�F��1���X�z��67���&�{Қ&T��>Pۓ�pᚓ� l���y	�����ܡ�����)���Ko������-�-�4+� [@ ��'b�T	��;ŪA�u�*9`_�����R�g�d~��[�v��(���*����e����*��.����6Z�E���	�qr�}\��Ꝙ�I�$A����
�p�bY2M�M:9��6��1����~F�Mx�w���6  