# Catur Jawa: Dam-daman over Reliable UDP

Dua proses Python independen memainkan Dam-daman Jawa melalui UDP sockets. Satu pemain bertindak sebagai
host yang otoritatif, sementara pemain lain bergabung sebagai client.

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

## Game Controls

Klik bidak, lalu klik tujuan yang disorot. History, actions, info, resync, coordinates,
dan resignation tersedia melalui drawer utilitas di sisi kanan.
