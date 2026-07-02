# 蜈ｬ髢句燕繝ｻ驕狗畑髢句ｧ句ｾ後ち繧ｹ繧ｯ謨ｴ逅・

譛邨よ峩譁ｰ: 2026-06-23

## 蜈ｬ髢句燕縺ｫ貎ｰ縺吶∋縺崎ｪｲ鬘・

| 蜆ｪ蜈・| 隱ｲ鬘・| 迥ｶ諷・| 谺｡縺ｮ遒ｺ隱・|
| --- | --- | --- | --- |
| S | README隱崎ｨｼ諠・ｱ蜑企勁 | 蟇ｾ蠢懈ｸ医∩縲ょ崋螳壹ユ繧ｹ繝医ヱ繧ｹ繝ｯ繝ｼ繝峨・蜀肴ｷｷ蜈･繧・`tests.unit.test_release_documentation` 縺ｧ讀懃衍 | 蜈ｬ髢句燕縺ｫ繝峨く繝･繝｡繝ｳ繝域､懃ｴ｢繧貞・螳溯｡・|
| S | Django繝舌・繧ｸ繝ｧ繝ｳ邨ｱ荳 | Django 5.2.15縺ｸ邨ｱ荳貂医∩ | 蜈ｨ繝・せ繝亥・螳溯｡・|
| S | 讓ｩ髯舌ユ繧ｹ繝・| 繧ｭ繝｣繝ｩ繧ｷ縲？O縲；M繝｡繝｢縺ｮ莉紋ｺｺ髢ｲ隕ｧ荳榊庄繧貞ｯｾ雎｡繝・せ繝医〒遒ｺ隱肴ｸ医∩ | 蜈ｬ髢句燕縺ｫ蜈ｨ讓ｩ髯舌ユ繧ｹ繝医ｒ蜀榊ｮ溯｡・|
| A | OAuth險ｭ螳夂｢ｺ隱・| 繝ｭ繝ｼ繧ｫ繝ｫ縺ｧ縺ｯ險ｭ螳夂憾諷玖｡ｨ遉ｺ縺ｮ縺ｿE2E蛹匁ｸ医∩ | Stg/Prod縺ｮGoogle縲．iscord縲々 callback繧貞ｮ溯ｪ榊庄縺ｧ遒ｺ隱・|
| A | 逕ｻ蜒上い繝・・繝ｭ繝ｼ繝芽ｲ闕ｷ隧ｦ鬨・| 1MB/5MB/荳企剞雜・℃縲）pg/png/gif繧定・蜍輔ユ繧ｹ繝亥喧縲ゅΟ繝ｼ繧ｫ繝ｫHTTP雋闕ｷ繝励Ο繝ｼ繝門ｮ溯｡梧ｸ医∩ | Stg/Prod逶ｸ蠖薙〒 `tests/performance/image_upload_load.py` 繧貞ｮ溯｡・|
| A | 繝舌ャ繧ｯ繧｢繝・・謇矩・ｽ懈・ | `docs/backup.md` 菴懈・貂医∩ | 譛ｬ逡ｪAWS蛟､縺ｧ蠕ｩ譌ｧ繝ｪ繝上・繧ｵ繝ｫ |

### OAuth Stg / Prod遒ｺ隱・

螳櫃lient ID縲ヾecret縲…allback縺ｮ螳溷､縺ｯ繝ｪ繝昴ず繝医Μ縺九ｉ縺ｯ遒ｺ隱阪〒縺阪∪縺帙ｓ縲ょ推Provider縺ｮ邂｡逅・判髱｢縺ｧ谺｡繧堤｢ｺ隱阪＠縺ｦ縺上□縺輔＞縲・

| Provider | Stg callback | Prod callback | 迥ｶ諷・|
| --- | --- | --- | --- |
| Google | `https://stg.tableno.jp/accounts/google/login/callback/` | `https://tableno.jp/accounts/google/login/callback/` | 譛ｪ遒ｺ隱・|
| Discord | `https://stg.tableno.jp/accounts/discord/login/callback/` | `https://tableno.jp/accounts/discord/login/callback/` | 譛ｪ遒ｺ隱・|
| X | `https://stg.tableno.jp/accounts/twitter_oauth2/login/callback/` | `https://tableno.jp/accounts/twitter_oauth2/login/callback/` | 譛ｪ遒ｺ隱・|

### 逕ｻ蜒上い繝・・繝ｭ繝ｼ繝芽ｲ闕ｷ隧ｦ鬨・

螳櫞TTP縺ｧ縺ｮ蜷梧凾繧｢繝・・繝ｭ繝ｼ繝臥｢ｺ隱阪・莉･荳九ｒ菴ｿ縺・∪縺吶・

```bash
python tests/performance/image_upload_load.py \
  --base-url http://127.0.0.1:8000 \
  --dev-login admin \
  --concurrency 4 \
  --requests-per-target 9
```

Stg/Prod逶ｸ蠖・

```bash
TABLENO_USERNAME=<operator-user> \
TABLENO_PASSWORD=<secret> \
python tests/performance/image_upload_load.py \
  --base-url https://stg.tableno.jp \
  --concurrency 8 \
  --requests-per-target 9
```

| 蟇ｾ雎｡ | 繧ｵ繧､繧ｺ | 蠖｢蠑・| 譛溷ｾ・ｵ先棡 |
| --- | --- | --- | --- |
| 繧ｭ繝｣繝ｩ逕ｻ蜒・| 1MB | jpg/png/gif | 謌仙粥 |
| 繧ｭ繝｣繝ｩ逕ｻ蜒・| 5MB | jpg/png/gif | 謌仙粥縺ｾ縺溘・荳企剞蠅・阜縺ｮ譏守｢ｺ縺ｪ繧ｨ繝ｩ繝ｼ |
| 繧ｭ繝｣繝ｩ逕ｻ蜒・| 荳企剞雜・℃ | jpg/png/gif | 400邉ｻ縲√お繝ｩ繝ｼ繝｡繝・そ繝ｼ繧ｸ陦ｨ遉ｺ |
| 繧ｷ繝翫Μ繧ｪ逕ｻ蜒・| 1MB | jpg/png/gif | 謌仙粥 |
| 繧ｷ繝翫Μ繧ｪ逕ｻ蜒・| 5MB | jpg/png/gif | 謌仙粥縺ｾ縺溘・荳企剞蠅・阜縺ｮ譏守｢ｺ縺ｪ繧ｨ繝ｩ繝ｼ |
| 繧ｷ繝翫Μ繧ｪ逕ｻ蜒・| 荳企剞雜・℃ | jpg/png/gif | 400邉ｻ縲√お繝ｩ繝ｼ繝｡繝・そ繝ｼ繧ｸ陦ｨ遉ｺ |
| 隍・焚譫夂匳骭ｲ | 騾壼ｸｸ2譫・/ 繝励Ξ繝溘い繝10譫・| jpg/png/gif豺ｷ蝨ｨ | 蜷・ｸ企剞蜀・〒謌仙粥縲∽ｸ企剞雜・℃繧・ｸ肴ｭ｣豺ｷ蜈･譎ゅ・譏守｢ｺ縺ｪ繧ｨ繝ｩ繝ｼ |
| 螟ｧ驥上い繧ｯ繧ｻ繧ｹ | 蜷梧凾繧｢繝・・繝ｭ繝ｼ繝・| jpg/png/gif豺ｷ蝨ｨ | worker縲．B縲ヾ3縲ヽedis縺梧椡貂・＠縺ｪ縺・|

## 驕狗畑髢句ｧ句ｾ後・隱ｲ鬘・

| 蜆ｪ蜈・| 隱ｲ鬘・| 譁ｹ驥・|
| --- | --- | --- |
| B | 蛻ｩ逕ｨ繝ｭ繧ｰ蜿朱寔 | 繝ｦ繝ｼ繧ｶ繝ｼ謨ｰ縲√そ繝・す繝ｧ繝ｳ菴懈・謨ｰ縲√く繝｣繝ｩ繧ｷ菴懈・謨ｰ縲・屬閼ｱ邇・ｒ髮・ｨ・|
| B | 繝輔ぅ繝ｼ繝峨ヰ繝・け蟆守ｷ・| 荳榊・蜷亥ｱ蜻翫∬ｦ∵悍繝輔か繝ｼ繝繧定ｨｭ鄂ｮ |
| B | 騾夂衍讖溯・謾ｹ蝟・| Discord騾夂衍縺ｨ繝｡繝ｼ繝ｫ騾夂衍縺ｮ驕狗畑隕∽ｻｶ繧呈紛逅・|

## 蟆・擂逧・↑謾ｹ蝟・

| 蜆ｪ蜈・| 隱ｲ鬘・| 譁ｹ驥・|
| --- | --- | --- |
| C | 繝｢繝・Ν蛻・牡 | 蟾ｨ螟ｧ縺ｪ `CharacterSheet` 繧・core/status/profile 縺ｪ縺ｩ縺ｸ谿ｵ髫主・蜑ｲ |
| C | API謨ｴ蛯・| 繧ｳ繧ｳ繝輔か繝ｪ繧｢縲．iscord Bot縲∝､夜Κ騾｣謳ｺ蜷代￠REST API繧呈紛逅・|
| C | 諤ｧ閭ｽ謾ｹ蝟・| 蛻ｩ逕ｨ閠・0莠ｺ雜・ｒ逶ｮ螳峨↓Redis繧ｭ繝｣繝・す繝･縲．B繧､繝ｳ繝・ャ繧ｯ繧ｹ縲√け繧ｨ繝ｪ譛驕ｩ蛹・|

## ﾎｲ蜈ｬ髢句燕縺ｮ驥咲せ遒ｺ隱・

- Playwright E2E: 譁ｰ隕冗匳骭ｲ縲√Γ繝ｼ繝ｫ繝ｭ繧ｰ繧､繝ｳ縲＾Auth險ｭ螳夂憾諷玖｡ｨ遉ｺ縲√そ繝・す繝ｧ繝ｳ菴懈・/邱ｨ髮・蜑企勁縲？O菴懈・/驟榊ｸ・髢ｲ隕ｧ蛻ｶ蠕｡縲√く繝｣繝ｩ繧ｷ菴懈・/邱ｨ髮・，CFOLIA JSON蜃ｺ蜉帙ｒ閾ｪ蜍慕｢ｺ隱肴ｸ医∩縲・
- 讓ｩ髯・ 莉紋ｺｺ縺ｮ繧ｭ繝｣繝ｩ繧ｷ縲？O縲；M繝｡繝｢縺瑚ｦ九∴縺ｪ縺・％縺ｨ繧貞ｯｾ雎｡繝・せ繝医〒遒ｺ隱肴ｸ医∩縲・
- 繝｢繝舌う繝ｫUI: Playwright縺ｧiPhone/Android逶ｸ蠖薙・繧ｻ繝・す繝ｧ繝ｳ荳隕ｧ縺ｨ繧ｭ繝｣繝ｩ繧ｷ邱ｨ髮・ｒ閾ｪ蜍慕｢ｺ隱肴ｸ医∩縲ょｮ滓ｩ溽｢ｺ隱阪・蜈ｬ髢句燕縺ｫ螳滓命縲・
- 繧ｨ繝ｩ繝ｼ繝壹・繧ｸ: 404縲・03縲・00縺ｮ繝・Φ繝励Ξ繝ｼ繝医ｒ謨ｴ蛯呎ｸ医∩縲り｡ｨ遉ｺ縺ｨ蟆守ｷ壹・蜈ｬ髢句燕縺ｫ謇句虚遒ｺ隱阪・
- 螟夜Κ萓晏ｭ・ OAuth螳溯ｪ榊庄縲ヾtg/Prod縺ｧ縺ｮ逕ｻ蜒剰ｲ闕ｷ縲∝ｮ滓ｩ溘Δ繝舌う繝ｫ遒ｺ隱阪・繝ｭ繝ｼ繧ｫ繝ｫ縺縺代〒縺ｯ螳御ｺ・ｸ榊庄縲・

## ﾎｲ蜈ｬ髢九せ繧ｳ繝ｼ繝・

ﾎｲ蜈ｬ髢九〒縺ｯ縲瑚ｿｷ繧上★菴ｿ縺医ｋ荳ｭ譬ｸ縲阪ｒ蜆ｪ蜈医＠縲∝､夜Κ騾｣謳ｺ繧・ｫ伜ｺｦ縺ｪ閾ｪ蜍募喧縺ｯ讀懆ｨｼ貂医∩縺ｮ遽・峇縺縺代ｒ陦ｨ遉ｺ繝ｻ驕狗畑縺励∪縺吶・

### ﾎｲ蜈ｬ髢九〒谿九☆荳ｭ譬ｸ

| 讖溯・ | ﾎｲ蜈ｬ髢九〒縺ｮ謇ｱ縺・| Go/No-Go遒ｺ隱・|
| --- | --- | --- |
| 繝ｭ繧ｰ繧､繝ｳ | 蠢・・| 騾壼ｸｸ繝ｭ繧ｰ繧､繝ｳ縲√Ο繧ｰ繧｢繧ｦ繝医√ヱ繧ｹ繝ｯ繝ｼ繝峨Μ繧ｻ繝・ヨ繝｡繝ｼ繝ｫ騾∽ｿ｡縲［andatory email verification縲∵悴遒ｺ隱阪Γ繝ｼ繝ｫ縺ｸ縺ｮ繝ｪ繧ｻ繝・ヨ繝｡繝ｼ繝ｫ謚第ｭ｢縲・莨壼ｰ守ｷ壹→譛牙柑縺ｪStripe雉ｼ隱ｭ荳ｭ縺ｮ蜑企勁繝悶Ο繝・け繧・`accounts.test_authentication`縲；oogle/Discord OAuth verified email驥崎､・凾縺ｮ譌｢蟄倥Θ繝ｼ繧ｶ繝ｼ蜀榊茜逕ｨ繧・`accounts.test_api_auth_google` / `accounts.test_api_auth_discord`縲々 API隱崎ｨｼ繧・`accounts.test_api_auth_twitter` 縺ｧ遒ｺ隱・|
| 繧ｰ繝ｫ繝ｼ繝・| 蠢・・| 繧ｰ繝ｫ繝ｼ繝怜､悶Θ繝ｼ繧ｶ繝ｼ縺碁撼蜈ｬ髢九げ繝ｫ繝ｼ繝・繧ｰ繝ｫ繝ｼ繝怜酷繧定ｦ九ｉ繧後↑縺・％縺ｨ |
| 繧ｻ繝・す繝ｧ繝ｳ邂｡逅・| 蠢・・| 菴懈・縲∫ｷｨ髮・∝炎髯､縲∝盾蜉閠・ｮ｡逅・√き繝ｬ繝ｳ繝繝ｼ陦ｨ遉ｺ繧堤｢ｺ隱・|
| Character sheets | Required | ShareLink scope tests: `accounts.tests.BasicAccountsTestCase.test_access_scope_private_update_closes_fixed_share_view` and fixed character sharing tests. |
| 遘伜諺HO | 蠢・・| GM縺ｯ蜈ｨ莉ｶ縲∝牡蠖撤L縺ｯ閾ｪ蛻・・HO縺ｮ縺ｿ縲∝・髢稀O縺ｯ蜿ょ刈閠・・蜩｡縲∵ｷｻ莉倥ｂ蜷後§讓ｩ髯舌〒遒ｺ隱・|
| 逕ｻ蜒上い繝・・繝ｭ繝ｼ繝・| 蠢・・| 繧ｭ繝｣繝ｩ繧ｷ/繧ｻ繝・す繝ｧ繝ｳ/繧ｷ繝翫Μ繧ｪ逕ｻ蜒上・菫晏ｭ倥∬｡ｨ遉ｺ縲√く繝｣繝ｩ繧ｷ逕ｻ蜒上・騾壼ｸｸ2譫・繝励Ξ繝溘い繝10譫壼宛髯舌∽ｸ企剞雜・℃譎ゅ・譏守｢ｺ縺ｪ繧ｨ繝ｩ繝ｼ |
| 譛菴朱剞縺ｮ繝励Ξ繝溘い繝蛻､螳・| 譚｡莉ｶ莉倥″ | Stripe Checkout縺ｯISSUE-077螳御ｺ・∪縺ｧ髱櫁｡ｨ遉ｺ縺ｾ縺溘・繝・せ繝医Δ繝ｼ繝蛾剞螳壹る°蝟ｶ繧ｳ繝ｼ繝・謇句虚莉倅ｸ弱・逶｣譟ｻ繝ｭ繧ｰ莉倥″縺ｧ遒ｺ隱・|

### ﾎｲ縺ｧ縺ｯ蠕悟屓縺励↓縺吶ｋ讖溯・

| 讖溯・ | ﾎｲ縺ｧ縺ｮ謇ｱ縺・| 逅・罰 |
| --- | --- | --- |
| Google Sheets騾｣謳ｺ | 蠕悟屓縺怜庄 | 繧ｳ繧｢菴馴ｨ薙〒縺ｯ縺ｪ縺・ょ､ｱ謨怜ｾｩ譌ｧ縺ｨ讓ｩ髯仙｢・阜縺ｮ螳溷慍遒ｺ隱榊ｾ後↓諡｡蠑ｵ |
| Google Calendar蜷梧悄 | 蠕悟屓縺怜庄 | 螟夜ΚOAuth/蜷梧悄螟ｱ謨玲凾縺ｮ驕狗畑雋闕ｷ縺碁ｫ倥＞ |
| Discord鬮伜ｺｦ騾夂衍 | 蠕悟屓縺怜庄 | Webhook險ｭ螳壹∝・騾√∝､ｱ謨礼屮隕悶・驕狗畑遒ｺ隱阪′蠢・ｦ・|
| WebSocket騾夂衍 | 蠕悟屓縺怜庄 | 繝昴・繝ｪ繝ｳ繧ｰ繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ縺後≠繧九◆繧∃ｲ蛻晄悄縺ｯ蠢・医〒縺ｯ縺ｪ縺・|
| 隍・尅縺ｪ閾ｪ蜍募・髢区擅莉ｶ | 蠕悟屓縺怜庄 | 遘伜諺HO縺ｮ謇句虚蜈ｬ髢九→蜊倡ｴ疲擅莉ｶ繧貞━蜈・|
| 鬮伜ｺｦ縺ｪ邨ｱ險・蟷ｴ髢薙・繝ｬ繧､譎る俣髮・ｨ・| 蠕悟屓縺怜庄 | ﾎｲ蛻晄悄縺ｮ萓｡蛟､讀懆ｨｼ縺ｫ縺ｯ荳崎ｦ・|

## 閠宣怫陬懷ｼｷ繝√ぉ繝・け繝ｪ繧ｹ繝・

| 鬆・岼 | 迥ｶ諷・| 險ｼ霍｡/遒ｺ隱阪さ繝槭Φ繝・|
| --- | --- | --- |
| 蜊ｱ髯ｺ繝輔ぃ繧､繝ｫ縺ｮGit邂｡逅・勁螟・| 繝ｭ繝ｼ繧ｫ繝ｫ蟇ｾ蠢懈ｸ医∩ | `cookies.txt`, `node_modules/`, `venv311/` 繧貞炎髯､蟇ｾ雎｡蛹悶Ａ.env*.example` 莉･螟悶・蜊ｱ髯ｺ繝代せ縺ｯ `git ls-files` 遒ｺ隱阪〒0莉ｶ縲～tests.unit.test_repository_hygiene` 縺ｧ閾ｪ蜍慕｢ｺ隱・|
| `.gitignore` 蜀咲｢ｺ隱・| 蟇ｾ蠢懈ｸ医∩ | `.env*` 縺ｯ髯､螟悶＠ `.env*.example` 縺ｮ縺ｿ霑ｽ霍｡蜿ｯ縲Ａnode_modules/`, `venv*/`, `cookies.txt`, `media/`, `staticfiles/`, `logs/`, `test-results/`, `playwright-report/` |
| Python/Docker邨ｱ荳 | 蟇ｾ蠢懈ｸ医∩ | README/AGENTS/CLAUDE/SPECIFICATION 縺ｯ Python 3.11+縲～.python-version` 縺ｯ 3.11縲．ockerfile 縺ｯ `python:3.11-slim` |
| CI最低ライン | 対応済み | `.github/workflows/django-ci.yml` で Python 3.11, `manage.py check`, `makemigrations --check --dry-run`, `migrate --check`, `pytest`, `flake8`, `black --check`, `isort --check`, Docker Compose config check, production deploy check, `billing_release_gate` |
| 譛ｬ逡ｪ隱崎ｨｼ險ｭ螳・| 蟇ｾ蠢懈ｸ医∩ | production settings 縺ｧ `ACCOUNT_EMAIL_VERIFICATION=mandatory`, `ACCOUNT_PREVENT_ENUMERATION=True`, `ACCOUNT_FORMS.reset_password=accounts.forms.CustomPasswordResetForm`縲ら峡閾ｪsignup/login縺ｧ繧よ悴遒ｺ隱阪Γ繝ｼ繝ｫ繧呈拠蜷ｦ縺励∵悴遒ｺ隱阪Γ繝ｼ繝ｫ縺ｸ縺ｮ繝代せ繝ｯ繝ｼ繝峨Μ繧ｻ繝・ヨ騾∽ｿ｡繧よ椛豁｢ |
| 蜈ｬ髢九・繝ｭ繝輔ぅ繝ｼ繝ｫ/API諠・ｱ驥・| 蟇ｾ蠢懈ｸ医∩ | Web profile 縺ｯ蜈ｱ譛峨げ繝ｫ繝ｼ繝怜ｿ・医°縺､繝｡繝ｼ繝ｫ髱櫁｡ｨ遉ｺ縲る壼ｸｸ `/api/accounts/users/<id>/` 縺ｯ譛ｬ莠ｺ莉･螟・04縲ゅげ繝ｫ繝ｼ繝・諡帛ｾ・繝輔Ξ繝ｳ繝芽ｩｳ邏ｰ縺ｯ蜈ｬ髢狗畑繝ｦ繝ｼ繧ｶ繝ｼ諠・ｱ縺ｮ縺ｿ |
| 蜈ｱ譛峨Μ繝ｳ繧ｯ縺ｮ諠・ｱ驥・| 蟇ｾ蠢懈ｸ医∩ | `accounts.test_share_links` 縺ｧ ShareLink 逋ｺ陦・螟ｱ蜉ｹ/譛滄剞蛻・ｌ縲～link` 縺ｨ `public` 縺ｮ蛻・屬縲√そ繝・す繝ｧ繝ｳ/繧ｭ繝｣繝ｩ繧ｯ繧ｿ繝ｼ/繧ｷ繝翫Μ繧ｪ/邨ｱ險亥・譛峨°繧臥ｧ伜諺HO縲；M繝｡繝｢縲∵園譛芽・繝ｦ繝ｼ繧ｶ繝ｼID/繝｡繝ｼ繝ｫ/claim諠・ｱ縺悟・縺ｪ縺・％縺ｨ繧堤｢ｺ隱・|
| 繝・・繝ｭ繧､襍ｷ蜍募・逅・・髮｢ | 蟇ｾ蠢懈ｸ医∩ | Stg/Prod縺ｯ `migrate` 縺ｨ `collectstatic` 繧・`up` 蜑阪↓譏守､ｺ螳溯｡後Ｆntrypoint縺ｯlocal/譏守､ｺ謖・ｮ壽凾縺ｮ縺ｿ螳溯｡後＠縲～tests.unit.test_docker_entrypoint` 縺ｧ `exec daphne`縲∬・蜍瀕igration譚｡莉ｶ縲，ompose `ENV_FILE` 蛻・屬繧堤｢ｺ隱・|
| 髱槫・髢九く繝｣繝ｩ繧ｷ逶ｴURL | 蟇ｾ蠢懈ｸ医∩ | `accounts.tests.BasicAccountsTestCase.test_fixed_character_share_view_requires_shareable_scope` 縺ｨ `accounts.tests.BasicAccountsTestCase.test_access_scope_private_update_closes_fixed_share_view`; group member character API uses `access_scope=public` via `accounts.test_group_features.GroupMemberCharactersAPITestCase.test_member_characters_only_include_public_scope` |
| 遘伜諺HO/API/豺ｻ莉俶ｨｩ髯・| 蟇ｾ蠢懈ｸ医∩ | `schedules.test_handout_permissions` 縺ｨ `schedules.test_session_visibility` 縺ｧ API/detail/attachment/public share URL/繧ｻ繝・す繝ｧ繝ｳ隧ｳ邏ｰ `handouts_detail` 繧堤｢ｺ隱阪らｧ伜諺HO豺ｻ莉倥・逶ｴURL DELETE縺ｯ蜑ｲ蠖灘､悶Θ繝ｼ繧ｶ繝ｼ縺ｸ404縺ｧ蟄伜惠遘伜諺縺励・夢隕ｧ蜿ｯ閭ｽ縺縺悟炎髯､讓ｩ髯舌′縺ｪ縺・盾蜉閠・・403縲Ｑrivate/group蜊薙・ `share_token` URL 縺ｯ404; stale or misdirected secret handout notifications are omitted from notification API list/detail/mark_read/unread_count/mark_all_read; scenario public API omits secret handout templates and creator private fields via `scenarios.test_scenarios.ScenarioAPITestCase.test_scenario_public_view_mode_is_readable_without_login` |
| Guest invitation management | 蟇ｾ蠢懈ｸ医∩ | `schedules.test_group_links_and_guests` 縺ｧ group admin create/revoke縲｛utsider 403縲∵悄髯仙・繧・螟ｱ蜉ｹ貂医∩諡帛ｾ・RL縺・10縺九▽繧ｻ繝・す繝ｧ繝ｳ隧ｳ邏ｰ繧定ｿ斐＆縺ｪ縺・％縺ｨ縲∝盾蜉譫claim縺ｯ `claim_token` 蠢・医〒縺ゅｋ縺薙→繧・`schedules.test_group_links_and_guests.GuestInvitationClaimTestCase.test_guest_claim_requires_invitation_token` 縺ｧ遒ｺ隱・|
| Stripe隱ｲ驥台ｺ区腐髦ｲ豁｢ | 繝ｭ繝ｼ繧ｫ繝ｫ蟇ｾ蠢懈ｸ医∩ | `accounts.test_billing`縲ＡSTRIPE_CHECKOUT_ENABLED` 縺ｯ騾壼ｸｸsettings/production/.env examples縺ｨ繧よ里螳哥alse縺ｧ縲√・繝ｫ繝代・/邂｡逅・さ繝槭Φ繝峨・險ｭ螳壽ｬ關ｽ譎ゅヵ繧ｩ繝ｼ繝ｫ繝舌ャ繧ｯ繧・alse縲よ・遉ｺTrue譎ゅ・縺ｿCheckout繧貞・縺吶・heckout/Customer Portal縺ｮStripe荳譎る囿螳ｳ譎ゅ・豎守畑503縺ｧ萓句､冶ｩｳ邏ｰ繧定ｿ斐＆縺ｪ縺・ょ､夜ΚStripe test-mode event ID遒ｺ隱阪・ISSUE-077縺ｨ縺励※譛ｪ螳後よ怏蜉ｹ縺ｪStripe雉ｼ隱ｭ荳ｭ縺ｮ繧｢繧ｫ繧ｦ繝ｳ繝亥炎髯､縺ｯ隱ｲ驥醍ｮ｡逅・・繝ｼ繧ｸ縺ｸ隱伜ｰ弱＠縺ｦ繝悶Ο繝・け |
| Docker螳溘ン繝ｫ繝・| 隕∝・遒ｺ隱・| `docker compose --env-file .env.compose.example config --quiet` 縺ｨ `docker compose --env-file .env.compose.example -f docker-compose.mysql.yml config --quiet` 縺ｯ謌仙粥縲る℃蜴ｻ縺ｫ `docker compose build --no-cache` 謌仙粥縲｜uild context邏・17KB縲Ｆntrypoint菫ｮ豁｣蠕後・螳溘ン繝ｫ繝峨・Docker daemon譛ｪ襍ｷ蜍輔〒譛ｪ螳・|
| 蜈ｨ菴薙ユ繧ｹ繝亥ｮ瑚ｵｰ | 繝ｭ繝ｼ繧ｫ繝ｫ遒ｺ隱肴ｸ医∩ | Python 3.11縺ｧ `manage.py test --noinput` 縺ｯ 1120莉ｶ OK縲《kipped=3 縺ｾ縺ｧ蛻ｰ驕斐る聞譎る俣螳溯｡後・邨ゆｺ・・逅・ｸｭ縺ｫ繧ｳ繝槭Φ繝峨Λ繝・ヱ繝ｼ縺ｯ timeout 謇ｱ縺・ら┌謖・ｮ壼ｮ溯｡後・繝励Ο繧ｸ繧ｧ繧ｯ繝域里螳壹Λ繝吶Ν縺ｫ髯仙ｮ壹＠縲」env/site-packages繧呈鏡繧上↑縺・|

## ﾎｲ蜈ｬ髢・Go/No-Go

| 蛻､螳夐・岼 | Go譚｡莉ｶ | 迴ｾ迥ｶ |
| --- | --- | --- |
| README騾壹ｊ縺ｫ繝ｭ繝ｼ繧ｫ繝ｫ襍ｷ蜍・| 譁ｰ隕冗腸蠅・〒 `migrate`, `runserver`, 繝ｭ繧ｰ繧､繝ｳ縺ｾ縺ｧ謌仙粥 | 譌｢蟄倥Ο繝ｼ繧ｫ繝ｫ迺ｰ蠅・〒 Python 3.11.1縲～manage.py check`縲～migrate --check`縲～runserver --noreload`縲～/health/live/`, `/health/ready/`, `/accounts/login/` 200 繧貞・遒ｺ隱肴ｸ医∩縲よ眠隕冗腸蠅・〒縺ｮ蜀咲樟遒ｺ隱阪・譛ｪ螳・|
| Docker襍ｷ蜍・| `docker compose build --no-cache` 縺ｨ `docker compose up` 縺梧・蜉・| 驕主悉縺ｫ `/health/live/` 縺ｨ `/health/ready/` 200繧堤｢ｺ隱阪Ｆntrypoint菫ｮ豁｣蠕後・蜀咲｢ｺ隱阪・Docker daemon譛ｪ襍ｷ蜍輔〒譛ｪ螳・|
| CI | GitHub Actions縺稽ain/PR縺ｧ謌仙粥 | 繝ｯ繝ｼ繧ｯ繝輔Ο繝ｼ霑ｽ蜉貂医∩縲√Ο繝ｼ繧ｫ繝ｫ蜷檎ｭ峨さ繝槭Φ繝峨・遒ｺ隱肴ｸ医∩縲ゅΜ繝｢繝ｼ繝亥ｮ溯｡後・譛ｪ遒ｺ隱阪・I billing_release_gate runs with STRIPE_CHECKOUT_ENABLED=False |
| production deploy check | production settings縺ｧ `check --deploy` 謌仙粥 | 繝ｭ繝ｼ繧ｫ繝ｫ遒ｺ隱肴ｸ医∩縲Ａtests.unit.test_production_settings` 縺ｧ CI 逶ｸ蠖・env 縺ｮ `manage.py check --deploy` 繧定・蜍慕｢ｺ隱・|
| 遘伜諺HO貍上ｌ縺ｪ縺・| 逶ｴURL/API/豺ｻ莉倥〒蜑ｲ蠖灘､悶Θ繝ｼ繧ｶ繝ｼ縺瑚ｦ九ｉ繧後↑縺・| 蟇ｾ雎｡繝・せ繝域ｸ医∩ |
| 髱槫・髢九く繝｣繝ｩ繧ｷ貍上ｌ縺ｪ縺・| API detail/public URL/逕ｻ髱｢URL縺ｧprivate縺瑚ｦ九∴縺ｪ縺・| 蟇ｾ雎｡繝・せ繝域ｸ医∩ |
| 繧ｰ繝ｫ繝ｼ繝怜､門酷貍上ｌ縺ｪ縺・| group/private蜊薙ｒ螟夜Κ繝ｦ繝ｼ繧ｶ繝ｼ縺瑚ｦ九ｉ繧後↑縺・| `manage.py test --noinput` 縺ｯ 1120莉ｶ OK縲《kipped=3 縺ｾ縺ｧ蛻ｰ驕斐＠縺ｦ蜀咲｢ｺ隱肴ｸ医∩ |
| Stripe迥ｶ諷九★繧後↑縺・| Checkout/Webhook/霑秘≡/逡ｰ隴ｰ/謇句虚/繝励Ο繝｢繧ｳ繝ｼ繝峨′逶｣譟ｻ繝ｭ繧ｰ莉倥″縺ｧ遒ｺ隱肴ｸ医∩ | 繝ｭ繝ｼ繧ｫ繝ｫ繝・せ繝域ｸ医∩縲ょ､夜ΚStripe遒ｺ隱阪・譛ｪ螳・|
| 繧ｨ繝ｩ繝ｼ逶｣隕・| Sentry/CloudWatch遲峨・騾夂衍蜈医′險ｭ螳壽ｸ医∩ | `SENTRY_DSN` 蟇ｾ蠢懊，loudWatch/SNS Runbook 縺ｨ Terraform 縺ｯ縺ゅｊ縲ょｮ欖NS雉ｼ隱ｭ/騾夂衍隧ｦ鬨薙・譛ｪ螳・|
| DB繝舌ャ繧ｯ繧｢繝・・ | 繝舌ャ繧ｯ繧｢繝・・/蠕ｩ譌ｧ謇矩・′螳溽腸蠅・〒遒ｺ隱肴ｸ医∩ | `docs/backup.md`, `docs/runbooks/AWS_DATABASE_MIGRATION.md`, RDS backup retention險ｭ螳壹≠繧翫ょｮ欒DS蠕ｩ譌ｧ繝ｪ繝上・繧ｵ繝ｫ縺ｯ譛ｪ螳・|
| 豕募漁/蝠上＞蜷医ｏ縺・| 蛻ｩ逕ｨ隕冗ｴ・√・繝ｩ繧､繝舌す繝ｼ繝昴Μ繧ｷ繝ｼ縲∫音蝠・ｳ戊｡ｨ遉ｺ縲∝撫縺・粋繧上○蜈医′譛ｬ逡ｪ螳溷､縺九▽豁｣蠑上Ξ繝薙Η繝ｼ貂医∩ | `/terms/`, `/privacy/`, `/contact/`, `/commercial-disclosure/` 縺ｨ `tests.unit.test_public_legal_pages`, `tests.unit.test_billing_legal_pages`, `billing_preflight --strict` 縺ｯ繝ｭ繝ｼ繧ｫ繝ｫ遒ｺ隱肴ｸ医∩縲よｭ｣蠑乗ｳ募漁繝ｬ繝薙Η繝ｼ縲・°蝟ｶ閠・ｮ溷､縲∝撫縺・粋繧上○蜈亥ｮ滄・騾∫｢ｺ隱阪・譛ｪ螳・|
| 邂｡逅・・｢ｺ隱・| 繝ｦ繝ｼ繧ｶ繝ｼ/隱ｲ驥醍憾諷・逶｣譟ｻ繝ｭ繧ｰ繧堤ｮ｡逅・判髱｢縺ｧ遒ｺ隱榊庄閭ｽ | `accounts.test_billing` 縺ｮ `BillingAdminTestCase` 縺ｧ繝ｦ繝ｼ繧ｶ繝ｼ/隱ｲ驥醍憾諷・逶｣譟ｻ繝ｭ繧ｰ縺ｮ陦ｨ遉ｺ繝ｻ繝輔ぅ繝ｫ繧ｿ繝ｻ謫堺ｽ懊ｒ繝ｭ繝ｼ繧ｫ繝ｫ遒ｺ隱肴ｸ医∩縲ょｮ歛ws-pre逶ｮ隕也｢ｺ隱阪・譛ｪ螳・|
