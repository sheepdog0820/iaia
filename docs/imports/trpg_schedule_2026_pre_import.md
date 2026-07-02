# TRPGスケジュール表2026 投入前確認

- Source: `\\NAS-CTHULHU\cthulhu\TRPGスケジュール表2026.xlsx`
- Generated at: `2026-06-20T06:58:27.397910+00:00`
- Past cutoff: `2026-06-20`
- Main sheet: `2026`
- Video sheet: `2026動画`

## Summary

- セッション候補: 40
- 過去対象: 39
- 未来対象: 1
- YouTube URLあり: 19
- 要確認: 22

## Usage

```bash
python manage.py import_trpg_schedule --excel-path "<TRPG schedule workbook.xlsx>" --output-json docs/imports/trpg_schedule_2026_pre_import.json --summary-md docs/imports/trpg_schedule_2026_pre_import.md --extract-only
python manage.py import_trpg_schedule --input-json docs/imports/trpg_schedule_2026_pre_import.json --dry-run
python manage.py import_trpg_schedule --input-json docs/imports/trpg_schedule_2026_pre_import.json --group-name "TRPGスケジュール表2026" --default-gm-username <username>
```

Current import supports Excel/JSON only. Direct legacy CSV import was removed before public release.

## 要確認セッション

- 2026-07-05 `未設定セッション 2026-07-05 row2` rows=[2] flags=blank_title, no_youtube_url
- 2026-06-02 `怪祓-カイブツ-` rows=[4, 5, 6, 7] flags=merged_rows, no_youtube_url
- 2026-05-31 `獣人ガストロノミー` rows=[8] flags=no_youtube_url
- 2026-05-30 `獣人ガストロノミー` rows=[9] flags=no_youtube_url
- 2026-05-30 `獣人ガストロノミー 事前導入HO3.4` rows=[10] flags=no_youtube_url
- 2026-05-25 `未設定セッション 2026-05-25 row13` rows=[13] flags=blank_title, no_youtube_url
- 2026-05-05 `怪祓-カイブツ-` rows=[14, 15, 16] flags=blank_kp, merged_rows, no_youtube_url
- 2026-05-04 `怪祓-カイブツ-` rows=[17, 18, 19] flags=blank_kp, merged_rows, no_youtube_url
- 2026-05-02 `Risoluto・Duo` rows=[20] flags=no_youtube_url
- 2026-04-25 `モーンガータの魔法使い` rows=[23] flags=unresolved_kp_or_members, no_youtube_url
- 2026-04-12 `静なるテロリスタ≪本編≫` rows=[26] flags=no_youtube_url
- 2026-04-11 `未設定セッション 2026-04-11 row27` rows=[27] flags=blank_title, no_youtube_url
- 2026-04-01 `モーンガータの魔法使い` rows=[29] flags=no_youtube_url
- 2026-03-11 `犬猫戦争は終わらせない` rows=[36] flags=unresolved_kp_or_members
- 2026-03-09 `未設定セッション 2026-03-09 row37` rows=[37] flags=blank_title, no_youtube_url
- 2026-02-18 `静なるテロリスタ≪本編≫` rows=[40] flags=no_youtube_url
- 2026-01-28 `狂気山脈 第一登山隊` rows=[41] flags=no_youtube_url
- 2026-01-18 `グレイブレコード` rows=[42] flags=no_youtube_url
- 2026-01-12 `静なるテロリスタ` rows=[45] flags=no_youtube_url
- 2026-01-07 `静なるテロリスタ【HO 異邦人】個別導入` rows=[46] flags=no_youtube_url
- 2026-01-03 `同じ空には昇れない【第三陣】` rows=[47] flags=no_youtube_url
- 2026-01-02 `静なるテロリスタ【HO童子】個別導入` rows=[48] flags=no_youtube_url

## 投入候補一覧

- 2026-07-05 `未設定セッション 2026-07-05 row2` KP=メイサイ PL=[ひめちゃん, ヤギ, ぬけ] rows=[2]
- 2026-06-06 `モーンガータの魔法使い` KP=メイサイ PL=[ぐん, ナエカ] rows=[3]
- 2026-06-02 `怪祓-カイブツ-` KP=しぇぱ PL=[メイサイ, 伊藤] rows=[4, 5, 6, 7]
- 2026-05-31 `獣人ガストロノミー` KP=シララ PL=[メイサイ, ひめちゃん, しぇぱ, 伊藤] rows=[8]
- 2026-05-30 `獣人ガストロノミー` KP=シララ PL=[メイサイ, ひめちゃん, しぇぱ, 伊藤] rows=[9]
- 2026-05-30 `獣人ガストロノミー 事前導入HO3.4` KP=シララ PL=[メイサイ, 伊藤] rows=[10]
- 2026-05-25 `ホームシック` KP=シララ PL=[メイサイ] rows=[11]
- 2026-05-25 `獣人ガストロノミー 事前導入HO1,2` KP=シララ PL=[ひめちゃん, しぇぱ] rows=[12]
- 2026-05-25 `未設定セッション 2026-05-25 row13` KP=シララ PL=[メイサイ] rows=[13]
- 2026-05-05 `怪祓-カイブツ-` KP=しぇぱ PL=[メイサイ, 伊藤] rows=[14, 15, 16]
- 2026-05-04 `怪祓-カイブツ-` KP=しぇぱ PL=[メイサイ, 伊藤] rows=[17, 18, 19]
- 2026-05-02 `Risoluto・Duo` KP=シララ PL=[メイサイ, ヤギ] rows=[20]
- 2026-05-01 `復元シマスカ？` KP=メイサイ PL=[伊藤, 村松, シララ] rows=[21]
- 2026-04-26 `モーンガータの魔法使い` KP=メイサイ PL=[じぇら, 九段] rows=[22]
- 2026-04-25 `モーンガータの魔法使い` KP=設定なし PL=[設定なし] rows=[23]
- 2026-04-19 `モーンガータの魔法使い` KP=メイサイ PL=[じぇら, 九段] rows=[24]
- 2026-04-15 `モーンガータの魔法使い` KP=メイサイ PL=[シララ, 伊藤] rows=[25]
- 2026-04-12 `静なるテロリスタ≪本編≫` KP=じぇら PL=[ヤギ, しぇぱ, 九段, ぬけ] rows=[26]
- 2026-04-11 `未設定セッション 2026-04-11 row27` KP=ひめちゃん PL=[じぇら, ヤギ] rows=[27]
- 2026-04-04 `モーンガータの魔法使い` KP=メイサイ PL=[ぐん, ナエカ] rows=[28]
- 2026-04-01 `モーンガータの魔法使い` KP=メイサイ PL=[シララ, 伊藤] rows=[29]
- 2026-03-27 `静なるテロリスタ【HO 異邦人】導入 ※冒頭録画ミス※ゴメンナサイ` KP=じぇら PL=[ぬけ] rows=[30]
- 2026-03-22 `静なるテロリスタ【HO 童子】導入` KP=じぇら PL=[ヤギ] rows=[31]
- 2026-03-21 `モーンガータの魔法使い` KP=メイサイ PL=[しぇぱ, ヤギ] rows=[32]
- 2026-03-17 `静なるテロリスタ【HO 美術家】導入` KP=じぇら PL=[九段] rows=[33]
- 2026-03-15 `モーンガータの魔法使い《後半》` KP=メイサイ PL=[ひめちゃん, ぬけ] rows=[34]
- 2026-03-14 `モーンガータの魔法使い《前半》` KP=メイサイ PL=[ひめちゃん, ぬけ] rows=[35]
- 2026-03-11 `犬猫戦争は終わらせない` KP=設定なし PL=[設定なし] rows=[36]
- 2026-03-09 `未設定セッション 2026-03-09 row37` KP=じぇら PL=[ひめちゃん, 伊藤] rows=[37]
- 2026-03-08 `モーンガーターの魔法使い` KP=メイサイ PL=[しぇぱ, ヤギ] rows=[38]
- 2026-03-07 `静なるテロリスタ【HO 篤学者】導入` KP=じぇら PL=[しぇぱ] rows=[39]
- 2026-02-18 `静なるテロリスタ≪本編≫` KP=じぇら PL=[メイサイ, シララ, ひめちゃん, 伊藤] rows=[40]
- 2026-01-28 `狂気山脈 第一登山隊` KP=じぇら PL=[メイサイ, シララ, 伊藤] rows=[41]
- 2026-01-18 `グレイブレコード` KP=メイサイ PL=[じぇら, ヤギ] rows=[42]
- 2026-01-17 `グレイブレコード` KP=メイサイ PL=[伊藤, ぬけ] rows=[43]
- 2026-01-12 `静なるテロリスタ【HO 篤学者】導入` KP=じぇら PL=[シララ] rows=[44]
- 2026-01-12 `静なるテロリスタ` KP=じぇら PL=[メイサイ, シララ] rows=[45]
- 2026-01-07 `静なるテロリスタ【HO 異邦人】個別導入` KP=じぇら PL=[伊藤] rows=[46]
- 2026-01-03 `同じ空には昇れない【第三陣】` KP=ひめちゃん PL=[じぇら, しぇぱ] rows=[47]
- 2026-01-02 `静なるテロリスタ【HO童子】個別導入` KP=じぇら PL=[ひめ] rows=[48]
