# Catur Jawa: Dam-daman over Reliable UDP

Dua proses Python independen memainkan Dam-daman Jawa melalui UDP sockets. Satu pemain bertindak sebagai
host yang otoritatif, sementara pemain lain bergabung sebagai client.

## Mandatory Implementation

- [x] Pemain A dan B bermain pada 2 program yang berbeda
- [x] Program berkomunikasi melewati socket UDP
- [x] Implementasikan protokol TCP atau protokol buatan sendiri di atas UDP untuk memastikan pengiriman berhasil
- [x] Permainan catur berjalan sesuai dengan aturan yang berlaku
- [x] Gunakan tc-netem untuk simulasi packet loss minimal 50% dan hapus rule setelah selesai (lihat `netem_run.sh`)
- [x] Pemain dapat memahami kondisi permainan (history pergerakan sendiri dan/atau lawan)

## Bonus Implementation

- [x] Buatlah GUI untuk permainan tersebut
- [ ] Mekanisme logging dilakukan di program terpisah (bukan program yang digunakan untuk melakukan permainan) dengan mengimplementasikan Raft untuk menjamin kebenarannya.
- [x] Buatlah sistem rating untuk seluruh player, perhitungan dibebaskan tetapi jangan gunakan perhitungan linear.
- [x] Buat video demo program (ajak 1 orang temen)

## Setup

### Build

```bash
git clone https://github.com/Naufal-Pinasthika/JIWA-JAWA
cd JIWA-JAWA
chmod +x scripts/bootstrap_linux.sh
./scripts/bootstrap_linux.sh
```

### Setup Tailscale VPN

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Pada [https://console.tailscale.com/admin/machines](https://console.tailscale.com/admin/machines), login akun
tailscale dan invite email temanmu agar dapat terhubung nantinya.

### Run

```bash
source .venv/bin/activate
python3 main.py
```

Ketik `Host`.

Sebagai host nanti, akan memberikan IP hasil dari tailscale, dan dapat digunakan ke diri sendiri untuk
dimainkan / teman lain.

Pada terminal lain / machine network lain, jalankan:

```bash
source .venv/bin/activate
python3 main.py
```

Ketik `Join` dan masukkan IP dari host.

### Test Packet Loss (tc-netem)

Cek interface aktif dengan `ip link` (untuk Tailscale biasanya `tailscale0`), lalu jalankan program di
bawah loss menggunakan `scripts/netem_run.sh`. Script ini mengaplikasikan 50% loss, menjalankan perintah,
dan menghapus rule otomatis saat selesai:

```bash
sudo ./scripts/netem_run.sh tailscale0 50 -- python3 main.py
```

Skrip netem lain di `scripts/`:
- `netem_apply.sh <iface> [loss%]` — terapkan loss (default 50%)
- `netem_clear.sh <iface>` — hapus rule netem

## Game Controls

Klik bidak, lalu klik tujuan yang disorot. History, actions, info, resync, coordinates,
dan resignation tersedia melalui drawer utilitas di sisi kanan.
