# FullCalendar 6.1.9

カレンダー表示とセッション作成フォームの初期化を外部CDNへの到達性に依存させないため、従来参照していた6.1.9を同梱する。バージョン更新ではない。

取得元: npmのfullcalendar@6.1.9配布アーカイブ（https://registry.npmjs.org/fullcalendar/-/fullcalendar-6.1.9.tgz）。npmメタデータのSHA-512 integrityとSHA-1（74b1baaab965d5dad1e4176191719e5d9ad85b1e）に一致することを確認した。JSとMITライセンスは配布ファイルを変更せず配置した。

| ファイル | SHA-256 |
| --- | --- |
| index.global.min.js | 6a5b22e8391ec5621d7950c472de6cedc9eab1680eaac8768a1b8865b53a1f72 |
| LICENSE.md | 4c0b0dae26c99e3b11be70b990a703be4deb75e21884104582e0e217786d3209 |

templates/schedules/calendar.htmlからDjango static経由で参照する。他の外部サービスやCDNを含むサイト全体のオフライン対応を示すものではない。
