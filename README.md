# SIEM dengan Elastic Stack: Deteksi Brute Force SSH

Proyek lab untuk membangun pipeline monitoring keamanan berbasis **Elastic Stack 8.19.0** (Elasticsearch, Kibana, Filebeat) yang berjalan dengan Docker Compose. Pipeline ini mengumpulkan log autentikasi SSH, menampilkannya di Kibana, dan memakai **custom detection rule** untuk mendeteksi serangan brute force.

> **Catatan keaslian data:** seluruh log dibuat oleh skrip `generate_logs.py` (simulasi) dengan IP sumber `192.0.2.10`, yaitu blok TEST-NET-1 yang dicadangkan untuk dokumentasi. Tidak ada sistem pihak lain yang diserang. Proyek ini untuk pembelajaran di lab pribadi.

Disusun oleh **Harun Yahya** (NIM 0110224032), mata kuliah CS-TVA-2504.

## Alur sistem

```
generate_logs.py -> logs/auth.log -> Filebeat -> Elasticsearch -> Kibana
 (log simulasi)     (JSON per baris)  (kurir)     (index:           (Discover, Rule,
                                                   filebeat-siem-lab)  Alerts)
```

## Struktur file

| File | Fungsi |
|---|---|
| `docker-compose.yml` | Menjalankan Elasticsearch, Kibana, Filebeat, dan container `setup` |
| `filebeat.yml` | Konfigurasi Filebeat: baca `auth.log`, parse JSON, kirim ke Elasticsearch |
| `generate_logs.py` | Simulator: menulis event gagal login SSH ke `logs/auth.log` |
| `logs/auth.log` | Log simulasi (satu event JSON per baris) |
| `.env.example` | Contoh variabel lingkungan (salin menjadi `.env`) |
| `.gitignore` | Mengecualikan `.env` agar password tidak ter-commit |

## Prasyarat

- Linux dengan Docker dan Docker Compose (diuji di VM Kali Linux).
- RAM minimal sekitar 4 GB untuk VM.
- Pengaturan memori untuk Elasticsearch:

```bash
sudo sysctl -w vm.max_map_count=262144
```

Tanpa ini, Elasticsearch bisa berhenti saat start.

## Cara menjalankan

1. Salin dan isi file lingkungan:

```bash
cp .env.example .env
nano .env
```

Isi `ELASTIC_PASSWORD` dan `KIBANA_PASSWORD` dengan password kuat. Untuk tiga kunci enkripsi Kibana, buat masing-masing dengan `openssl rand -hex 16` (minimal 32 karakter).

2. Validasi dan jalankan:

```bash
docker compose config > /dev/null && echo "File OK"
docker compose up -d
docker compose ps -a
```

Hasil yang benar: `siem-elasticsearch` Up (healthy), `siem-kibana` dan `siem-filebeat` Up, `siem-setup` **Exited (0)** (normal, container ini hanya mengatur password user `kibana_system`).

3. Buka Kibana di `http://localhost:5601` dan login dengan user `elastic`. Tunggu 1 sampai 3 menit setelah container berjalan.

## Membuat log simulasi

```bash
python3 generate_logs.py        # 8 event
python3 generate_logs.py 4      # jumlah event dapat diatur
```

Setiap event memuat `@timestamp`, `event.category: authentication`, `event.outcome: failure`, `source.ip`, `process.name: sshd`, dan `message` bergaya log SSH. Jeda antar event 2 detik.

Verifikasi data masuk ke Elasticsearch:

```bash
curl -u elastic:PASSWORD_ANDA "http://localhost:9200/filebeat-siem-lab/_count?pretty"
```

Jumlah dokumen bertambah mengikuti jumlah baris di `auth.log`. Tunggu sekitar 30 detik setelah container baru berjalan, karena Filebeat memindai file per interval.

## Monitoring di Kibana

1. **Data view:** Stack Management, Data Views, buat `SIEM Lab` dengan index pattern `filebeat-siem-lab*` dan timestamp `@timestamp`.
2. **Discover:** pilih data view `SIEM Lab`, rentang waktu Last 24 hours, filter `event.outcome : "failure"`.
3. **Dashboard:** buat dashboard dengan Lens, misalnya Total Events (Metric), Failed Logins Over Time (Bar vertical), dan Top Source IP (Table).

## Custom detection rule

Dibuat di Kibana Security, Rules, Detection rules (SIEM).

| Parameter | Nilai |
|---|---|
| Nama | SSH Brute Force Attempt |
| Tipe | Threshold |
| Index pattern | `filebeat-siem-lab*` |
| Query (KQL) | `event.category : "authentication" and event.outcome : "failure"` |
| Threshold | Group by `source.ip`, nilai `>= 6` |
| Severity / Risk score | High / 73 |
| MITRE ATT&CK | Credential Access (TA0006), Brute Force (T1110) |
| Jadwal | Tiap 5 menit, additional look-back 1 menit |

Untuk memicu alert, jalankan `python3 generate_logs.py 8` **setelah rule aktif**, lalu tunggu sekitar 5 sampai 6 menit. Event lama di luar jendela pemeriksaan tidak memicu rule. Hasilnya satu alert per IP (bukan per event), karena rule Threshold mengelompokkan event per `source.ip`. Detail alert dapat dilihat di Security, Alerts.

## Hasil uji

Dari 8 event simulasi, rule menghasilkan 1 alert berseverity High dengan `source.ip` 192.0.2.10 dan `kibana.alert.threshold_result.count` = 8.

## Keterbatasan

- Log berasal dari simulasi, bukan serangan nyata.
- Serangan yang sangat lambat dan brute force terdistribusi dari banyak IP tidak terdeteksi, karena rule menghitung per IP dalam jendela waktu pendek.
- Rule hanya mendeteksi, tidak memblokir. Pemblokiran membutuhkan alat seperti fail2ban atau firewall.
- Konfigurasi lab ini tidak layak untuk produksi: HTTPS Elasticsearch dimatikan (`xpack.security.http.ssl.enabled=false`), dan nama container ditetapkan tetap sehingga hanya satu stack yang dapat berjalan per mesin.

## Pembersihan

```bash
docker compose stop        # hentikan container, data tetap
docker compose down        # hapus container, data di volume tetap
docker compose down -v     # hapus container DAN data (dashboard dan log ikut hilang)
```

## Keamanan repositori

File `.env` berisi password dan kunci enkripsi, sehingga dikecualikan lewat `.gitignore`. Jangan pernah meng-commit `.env` atau token akses GitHub.
