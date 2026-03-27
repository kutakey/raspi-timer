# Raspberry Pi カウントダウンタイマー

7インチ公式タッチディスプレイ（800x480）向けタイマーアプリ

## セットアップ

### 必要なもの
- Raspberry Pi 4
- Raspberry Pi 公式7インチタッチディスプレイ
- Python 3
- pygame

### インストール

```bash
# pygameインストール
pip3 install pygame

# Tkinterは通常プリインストール済み
# もしなければ:
sudo apt install python3-tk
```

### 実行

```bash
python3 timer_app.py
```

### 自動起動設定（Raspberry Pi）

```bash
# autostart設定
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/timer.desktop << EOF
[Desktop Entry]
Type=Application
Name=Timer
Exec=python3 /home/pi/raspi-timer/timer_app.py
EOF
```

## 操作方法

| 操作 | 動作 |
|------|------|
| タイマー表示タッチ | スタート / ストップ |
| ↑ボタン | +1分（停止時のみ） |
| ↓ボタン | -1分（停止時のみ） |
| 🔈ボタン | 音量スライダー展開/収納 |
| アラーム中にタッチ | アラーム停止 & リセット |
| ESCキー | 全画面解除（開発用） |

## 設定範囲

- タイマー: 1分〜99分
- 音量: 0%〜100%（amixer経由）
