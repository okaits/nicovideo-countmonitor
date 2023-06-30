# nicovideo-countmonitor
## What's this
ニコニコ動画から指定された動画の再生数とかを取得して、継続的に出力するスクリプトです。  
ログファイルに記録することもできます。

## 使い方
### 初期設定とか
Python3とrequirements.txtをインストールしましょう

### 使い方１: モニター
取得したデータを継続的に出力します  
構文:
```bash
main.py -v 動画ID -c 出力回数(デフォルト: 無限) -l ログファイル(デフォルト: 記録しない) -i インターバル(デフォルト: 10, 単位: sec)
```

### 使い方２: リプレイ
ログファイルに記録された情報を人間に読める形で出力します  
構文:
```bash
main.py -r -l ログファイル -v 動画ID(デフォルト: 全て) -c 出力件数(デフォルト: 全て)
```

## License
GNU General Public License  
Copyright © 2023 okaits#7534
