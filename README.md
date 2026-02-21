<p align="center">
  <img src="https://img.shields.io/badge/discord.py-2.6+-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="discord.py">
  <img src="https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="License">
</p>

# Discord All-in-One Bot

Bot Discord **đa năng** tích hợp **phát nhạc YouTube**, **hệ thống log toàn diện**, và **quản lý server** trong một file duy nhất. Dễ cài, dễ dùng, dễ tuỳ chỉnh.

---

## Tính năng

### Phát nhạc YouTube
- Tìm kiếm bằng tên hoặc dán link YouTube trực tiếp
- Hàng đợi nhạc (queue) riêng biệt cho từng server
- Âm thanh được xử lý qua bộ lọc chuyên nghiệp (bass boost, compressor, limiter)
- Chỉnh âm lượng realtime — không cần restart bài
- Bot treo trong kênh thoại cho đến khi bạn đuổi

### Hệ thống Log toàn diện
- Bắt tin nhắn bị xóa (snipe) và gửi lại ngay tại kênh
- Theo dõi voice: join, leave, chuyển kênh
- Theo dõi thành viên vào/ra server
- Phát hiện thay đổi biệt danh
- Kênh log lưu vào JSON — restart bot không mất cấu hình

### Quản lý Server
- Tạo role với màu tuỳ chỉnh
- Cấp role cho thành viên
- Xoá tin nhắn hàng loạt (nuke) với file backup tự động

---

## Danh sách lệnh

### Nhạc

| Lệnh | Mô tả |
|---|---|
| `/play <tên hoặc link>` | Phát nhạc hoặc thêm vào hàng đợi |
| `/skip` | Bỏ qua bài đang phát |
| `/stop` | Dừng nhạc, xoá hàng đợi (bot vẫn ở kênh) |
| `/queue` | Xem danh sách hàng đợi |
| `/volume <0-100>` | Chỉnh âm lượng |
| `/leave` | Bot rời khỏi kênh thoại |

### Quản lý

| Lệnh | Quyền cần | Mô tả |
|---|---|---|
| `/setlog <kênh>` | Admin | Thiết lập kênh log |
| `/createrole <tên> [màu]` | Manage Roles | Tạo role mới |
| `/addrole <người> <role>` | Manage Roles | Cấp role cho thành viên |
| `/nuke <1-150>` | Manage Messages | Xoá tin nhắn + backup file .txt |

### Khác

| Lệnh | Mô tả |
|---|---|
| `!av [@người]` | Xem avatar (prefix command) |

---

## Cài đặt

### Yêu cầu hệ thống

- [Python](https://www.python.org/downloads/) 3.10 trở lên
- [FFmpeg](https://ffmpeg.org/download.html) (bắt buộc cho phát nhạc)

### 1. Clone repo

```bash
git clone https://github.com/dkhoasobad/Discord-Bot-Basic
cd Discord-Bot-Basic
```

### 2. Cài dependencies

```bash
pip install -r requirements.txt
```

### 3. Cài FFmpeg

<details>
<summary><b>Windows</b></summary>

1. Tải FFmpeg tại [ffmpeg.org/download](https://ffmpeg.org/download.html) hoặc [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
2. Giải nén, copy đường dẫn thư mục `bin/`
3. Thêm vào **System Environment Variables → Path**
4. Mở CMD mới, gõ `ffmpeg -version` để kiểm tra

</details>

<details>
<summary><b>Linux (Ubuntu/Debian)</b></summary>

```bash
sudo apt update && sudo apt install ffmpeg -y
```

</details>

<details>
<summary><b>macOS</b></summary>

```bash
brew install ffmpeg
```

</details>

### 4. Cấu hình Token

Mở file `bot.py`, thay token ở dòng cuối:

```python
bot.run('TOKEN_CỦA_BẠN')
```

> Lấy token tại [Discord Developer Portal](https://discord.com/developers/applications)

### 5. Bật Intents

Tại **Discord Developer Portal → Bot → Privileged Gateway Intents**, bật:

- [x] **Message Content Intent**
- [x] **Server Members Intent**

### 6. Chạy bot

```bash
python bot.py
```

---

## Cấu trúc dự án

```
discordbot/
├── bot.py                 # Toàn bộ source code
├── log_channels.json      # Tự tạo — lưu cấu hình kênh log
├── requirements.txt       # Dependencies
└── README.md
```

---

## Tuỳ chỉnh âm thanh

Chỉnh các thông số trong `FFMPEG_OPTIONS` ở đầu file `bot.py`:

```python
FFMPEG_OPTIONS = {
    'options': '-vn -af "aresample=48000,bass=g=2,treble=g=-2,acompressor=...,alimiter=...,volume=1.3"'
}
```

| Tham số | Ý nghĩa | Giá trị gợi ý |
|---|---|---|
| `bass=g=` | Tăng/giảm bass (dB) | `0` đến `5` |
| `treble=g=` | Tăng/giảm treble (dB) | `-3` đến `3` |
| `volume=` | Khuếch đại tín hiệu | `1.0` đến `1.5` |
| `alimiter=limit=` | Ngưỡng chống rè | `0.9` đến `1.0` |

---

## Tech Stack

| Thành phần | Công nghệ |
|---|---|
| Framework | [discord.py](https://discordpy.readthedocs.io/) 2.6+ |
| Trích xuất YouTube | [yt-dlp](https://github.com/yt-dlp/yt-dlp) |
| Xử lý audio | [FFmpeg](https://ffmpeg.org/) |
| Voice encryption | [PyNaCl](https://pynacl.readthedocs.io/) |
| Ngôn ngữ | Python 3.10+ |

---

## License

Dự án này được phân phối dưới giấy phép [MIT](LICENSE). Thoải mái sử dụng, chỉnh sửa và chia sẻ.
