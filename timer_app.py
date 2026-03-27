#!/usr/bin/env python3
"""
Raspberry Pi カウントダウンタイマー
7インチ公式タッチディスプレイ（800x480）向け
"""

import tkinter as tk
import subprocess
import platform
import math
import struct
import wave
import io
import os
import tempfile

# pygame初期化（アラーム音用）
try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("WARNING: pygame not available. Alarm sound disabled.")


class TimerApp:
    # カラー定義
    COLOR_BG = "#FFFFFF"
    COLOR_TIMER_NORMAL = "#000000"
    COLOR_TIMER_ALARM = "#FF0000"
    COLOR_UP_BTN = "#CC6600"
    COLOR_DOWN_BTN = "#1E6E8E"
    COLOR_VOLUME_BTN = "#888888"
    COLOR_ARROW = "#F4A580"      # サーモンピンク（矢印アイコン）
    COLOR_SPEAKER = "#555555"    # ダークグレー（スピーカーアイコン）
    COLOR_SLIDER_BG = "#E0E0E0"
    COLOR_SLIDER_FILL = "#4A90D9"
    COLOR_SLIDER_KNOB = "#FFFFFF"

    # 画面サイズ
    WIDTH = 800
    HEIGHT = 480

    # ボタン幅
    BTN_WIDTH = 120

    def __init__(self, root):
        self.root = root
        self.root.title("Timer")
        self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.root.configure(bg=self.COLOR_BG)
        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", lambda e: self.root.attributes("-fullscreen", False))

        # タイマー状態
        self.set_minutes = 5  # 初期設定分
        self.remaining_seconds = self.set_minutes * 60
        self.running = False
        self.alarming = False
        self.timer_id = None

        # 音量状態
        self.volume = 70  # 0-100
        self.volume_slider_open = False
        self.slider_dragging = False

        # アラーム音生成
        self.alarm_sound = None
        if PYGAME_AVAILABLE:
            self._generate_alarm_sound()

        # UI構築
        self._build_ui()
        self._update_display()

    def _generate_alarm_sound(self):
        """ビープ音を動的生成"""
        sample_rate = 44100
        duration = 0.5  # 秒
        frequency = 1000  # Hz
        n_samples = int(sample_rate * duration)

        # ビープ音波形生成
        buf = io.BytesIO()
        with wave.open(buf, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            for i in range(n_samples):
                t = i / sample_rate
                # ビープ音（サイン波） + エンベロープ
                envelope = 1.0
                if i < 500:
                    envelope = i / 500.0
                elif i > n_samples - 500:
                    envelope = (n_samples - i) / 500.0
                value = int(32767 * envelope * math.sin(2 * math.pi * frequency * t))
                wf.writeframes(struct.pack('<h', value))

        buf.seek(0)

        # 一時ファイルに保存してpygameで読み込み
        self._temp_sound_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        self._temp_sound_file.write(buf.read())
        self._temp_sound_file.flush()
        self.alarm_sound = pygame.mixer.Sound(self._temp_sound_file.name)

    def _build_ui(self):
        """UIを構築"""
        # メインフレーム
        self.main_frame = tk.Frame(self.root, bg=self.COLOR_BG)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # タイマー表示エリア（左側）
        timer_width = self.WIDTH - self.BTN_WIDTH
        self.timer_canvas = tk.Canvas(
            self.main_frame,
            width=timer_width,
            height=self.HEIGHT,
            bg=self.COLOR_BG,
            highlightthickness=0
        )
        self.timer_canvas.place(x=0, y=0)
        self.timer_canvas.bind("<Button-1>", self._on_timer_click)

        # タイマーテキスト（イタリック太字）
        self.timer_text = self.timer_canvas.create_text(
            timer_width // 2,
            self.HEIGHT // 2 - 10,
            text="05:00",
            font=("Helvetica", 150, "bold italic"),
            fill=self.COLOR_TIMER_NORMAL
        )

        # 右側ボタンエリア
        btn_height = self.HEIGHT // 3

        # ↑ボタン（オレンジ）
        self.up_canvas = tk.Canvas(
            self.main_frame,
            width=self.BTN_WIDTH,
            height=btn_height,
            bg=self.COLOR_UP_BTN,
            highlightthickness=0
        )
        self.up_canvas.place(x=self.WIDTH - self.BTN_WIDTH, y=0)
        self._draw_arrow_up(self.up_canvas, self.BTN_WIDTH, btn_height)
        self.up_canvas.bind("<Button-1>", self._on_up)

        # ↓ボタン（青）
        self.down_canvas = tk.Canvas(
            self.main_frame,
            width=self.BTN_WIDTH,
            height=btn_height,
            bg=self.COLOR_DOWN_BTN,
            highlightthickness=0
        )
        self.down_canvas.place(x=self.WIDTH - self.BTN_WIDTH, y=btn_height)
        self._draw_arrow_down(self.down_canvas, self.BTN_WIDTH, btn_height)
        self.down_canvas.bind("<Button-1>", self._on_down)

        # 音量ボタン（グレー）
        self.vol_canvas = tk.Canvas(
            self.main_frame,
            width=self.BTN_WIDTH,
            height=btn_height,
            bg=self.COLOR_VOLUME_BTN,
            highlightthickness=0
        )
        self.vol_canvas.place(x=self.WIDTH - self.BTN_WIDTH, y=btn_height * 2)
        self._draw_speaker_icon(self.vol_canvas, self.BTN_WIDTH, btn_height)
        self.vol_canvas.bind("<Button-1>", self._on_volume_btn)

        # 音量スライダーオーバーレイ（初期非表示）
        self.slider_frame = tk.Frame(self.main_frame, bg=self.COLOR_SLIDER_BG, bd=2, relief=tk.RAISED)
        self.slider_canvas = tk.Canvas(
            self.slider_frame,
            width=280,
            height=80,
            bg=self.COLOR_SLIDER_BG,
            highlightthickness=0
        )
        self.slider_canvas.pack(padx=10, pady=10)
        self.slider_canvas.bind("<Button-1>", self._on_slider_click)
        self.slider_canvas.bind("<B1-Motion>", self._on_slider_drag)

    def _draw_arrow_up(self, canvas, w, h):
        """↑太い矢印を描画（矢じり+軸）"""
        cx, cy = w // 2, h // 2
        # 矢じり（三角形）
        canvas.create_polygon(
            cx, cy - 30,
            cx - 28, cy,
            cx + 28, cy,
            fill=self.COLOR_ARROW, outline=self.COLOR_ARROW
        )
        # 軸（太い長方形）
        canvas.create_rectangle(
            cx - 10, cy, cx + 10, cy + 28,
            fill=self.COLOR_ARROW, outline=self.COLOR_ARROW
        )

    def _draw_arrow_down(self, canvas, w, h):
        """↓太い矢印を描画（矢じり+軸）"""
        cx, cy = w // 2, h // 2
        # 軸（太い長方形）
        canvas.create_rectangle(
            cx - 10, cy - 28, cx + 10, cy,
            fill=self.COLOR_ARROW, outline=self.COLOR_ARROW
        )
        # 矢じり（三角形）
        canvas.create_polygon(
            cx, cy + 30,
            cx - 28, cy,
            cx + 28, cy,
            fill=self.COLOR_ARROW, outline=self.COLOR_ARROW
        )

    def _draw_speaker_icon(self, canvas, w, h):
        """スピーカーアイコンを描画（アウトラインスタイル）"""
        cx, cy = w // 2, h // 2
        lw = 3  # 線の太さ
        # スピーカー本体（アウトライン）
        canvas.create_rectangle(
            cx - 18, cy - 10, cx - 6, cy + 10,
            fill="", outline=self.COLOR_SPEAKER, width=lw
        )
        # スピーカーコーン（アウトライン）
        canvas.create_polygon(
            cx - 6, cy - 10,
            cx + 10, cy - 22,
            cx + 10, cy + 22,
            cx - 6, cy + 10,
            fill="", outline=self.COLOR_SPEAKER, width=lw
        )
        # 音波（弧）
        for r in [18, 26]:
            canvas.create_arc(
                cx + 4 - r, cy - r,
                cx + 4 + r, cy + r,
                start=-40, extent=80,
                style=tk.ARC,
                outline=self.COLOR_SPEAKER,
                width=lw
            )

    def _draw_slider(self):
        """音量スライダーを描画"""
        c = self.slider_canvas
        c.delete("all")
        w, h = 280, 80

        # スピーカーミニアイコン（左端）
        c.create_text(10, h // 2, text="🔈", font=("Helvetica", 16), anchor=tk.W)

        # スライダートラック
        track_x1 = 45
        track_x2 = w - 15
        track_y = h // 2
        track_len = track_x2 - track_x1
        c.create_rectangle(
            track_x1, track_y - 4, track_x2, track_y + 4,
            fill="#CCCCCC", outline="#CCCCCC"
        )

        # フィル部分
        fill_x = track_x1 + (self.volume / 100.0) * track_len
        c.create_rectangle(
            track_x1, track_y - 4, fill_x, track_y + 4,
            fill=self.COLOR_SLIDER_FILL, outline=self.COLOR_SLIDER_FILL
        )

        # ノブ
        c.create_oval(
            fill_x - 12, track_y - 12, fill_x + 12, track_y + 12,
            fill=self.COLOR_SLIDER_KNOB, outline="#999999", width=2
        )

        # 音量パーセント
        c.create_text(
            w // 2, h - 8,
            text=f"{self.volume}%",
            font=("Helvetica", 12),
            fill="#666666"
        )

    def _on_timer_click(self, event):
        """タイマーエリアクリック"""
        if self.alarming:
            # アラーム停止 & リセット
            self._stop_alarm()
            self.remaining_seconds = self.set_minutes * 60
            self.running = False
            self._update_display()
        elif self.running:
            # ストップ
            self.running = False
            if self.timer_id:
                self.root.after_cancel(self.timer_id)
                self.timer_id = None
        else:
            # スタート
            if self.remaining_seconds > 0:
                self.running = True
                self._tick()

        # 音量スライダーが開いてたら閉じる
        if self.volume_slider_open:
            self._toggle_slider(False)

    def _on_up(self, event):
        """↑ボタン: +1分"""
        if not self.running and not self.alarming:
            self.set_minutes = min(99, self.set_minutes + 1)
            self.remaining_seconds = self.set_minutes * 60
            self._update_display()

    def _on_down(self, event):
        """↓ボタン: -1分"""
        if not self.running and not self.alarming:
            self.set_minutes = max(1, self.set_minutes - 1)
            self.remaining_seconds = self.set_minutes * 60
            self._update_display()

    def _on_volume_btn(self, event):
        """音量ボタンクリック"""
        self._toggle_slider(not self.volume_slider_open)

    def _toggle_slider(self, show):
        """音量スライダーの表示/非表示"""
        self.volume_slider_open = show
        if show:
            # ボタンの左側に表示
            sx = self.WIDTH - self.BTN_WIDTH - 310
            sy = self.HEIGHT - 120
            self.slider_frame.place(x=sx, y=sy)
            self._draw_slider()
        else:
            self.slider_frame.place_forget()

    def _on_slider_click(self, event):
        """スライダーのクリック/タップ"""
        self._update_volume_from_pos(event.x)

    def _on_slider_drag(self, event):
        """スライダーのドラッグ"""
        self._update_volume_from_pos(event.x)

    def _update_volume_from_pos(self, x):
        """スライダー位置から音量を更新"""
        track_x1 = 45
        track_x2 = 265
        track_len = track_x2 - track_x1
        vol = int(((x - track_x1) / track_len) * 100)
        self.volume = max(0, min(100, vol))
        self._draw_slider()
        self._set_system_volume(self.volume)

    def _set_system_volume(self, vol):
        """システム音量を設定"""
        try:
            if platform.system() == "Linux":
                # Raspberry Pi (ALSA)
                subprocess.run(
                    ["amixer", "sset", "Master", f"{vol}%"],
                    capture_output=True, timeout=2
                )
            elif platform.system() == "Darwin":
                # macOS（開発用）
                osascript_vol = int(vol * 7 / 100)
                subprocess.run(
                    ["osascript", "-e", f"set volume output volume {vol}"],
                    capture_output=True, timeout=2
                )
        except Exception as e:
            print(f"Volume control error: {e}")

    def _tick(self):
        """毎秒のカウントダウン"""
        if not self.running:
            return

        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self._update_display()
            self.timer_id = self.root.after(1000, self._tick)
        else:
            # 00:00到達 → アラーム
            self._update_display()
            self._start_alarm()

    def _update_display(self):
        """タイマー表示を更新"""
        mins = self.remaining_seconds // 60
        secs = self.remaining_seconds % 60
        time_str = f"{mins:02d}:{secs:02d}"

        color = self.COLOR_TIMER_ALARM if self.alarming else self.COLOR_TIMER_NORMAL
        self.timer_canvas.itemconfig(self.timer_text, text=time_str, fill=color)

    def _start_alarm(self):
        """アラーム鳴動開始"""
        self.alarming = True
        self.running = False
        self._update_display()

        if PYGAME_AVAILABLE and self.alarm_sound:
            self.alarm_sound.play(loops=-1)  # 無限ループ

    def _stop_alarm(self):
        """アラーム停止"""
        self.alarming = False
        if PYGAME_AVAILABLE and self.alarm_sound:
            self.alarm_sound.stop()

    def cleanup(self):
        """クリーンアップ"""
        if PYGAME_AVAILABLE:
            pygame.mixer.quit()
        if hasattr(self, '_temp_sound_file'):
            try:
                os.unlink(self._temp_sound_file.name)
            except:
                pass


def main():
    root = tk.Tk()
    app = TimerApp(root)

    def on_close():
        app.cleanup()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
