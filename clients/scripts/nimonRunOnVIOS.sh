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
��F�`nimonRunOnVIOS.sh ���n�0@��������i:��a��Re���
�Ȇ�6ɿ��e�-g?ߙ��qଥ�F�f�@��q�@^K�|8xFє	� j�J��k�lD���:��@cn��(x)J�2p"�M�o����1���X�z���6���x�=iM�YO���M�p��_ �������|�X���_�|�$߃�K���\���A/oKy#�J.���;f �F���N�j�]��L��3=�qz����8�_�疪��=/
$o�J$9�uY��5��g�fZ}p�ܢSq��89�>.H��N�~�$F� QHLǪ��pSdy2e�M:=��6��1����~F��������8  