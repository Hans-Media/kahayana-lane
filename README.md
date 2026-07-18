# kahayana-lane — Auto-post Threads dari Notion

Script ini jalan otomatis lewat GitHub Actions tiap 30 menit, baca konten
dari database Notion "Threads Content Queue" yang statusnya **Terjadwal**,
lalu posting ke Threads. Baris dengan "Thread Group" yang sama dirangkai
jadi satu thread (reply-chain), diurutkan pakai kolom "Urutan".

## Setup (sekali doang)

Repo ini butuh 2 **secret** dan 1 **variable** di GitHub, isi lewat:
Settings → Secrets and variables → Actions

### Secrets (Repository secrets)

| Nama | Isi |
|---|---|
| `THREADS_ACCESS_TOKEN` | Long-lived access token dari Meta Developer App (diawali `THAA`) |
| `NOTION_TOKEN` | Token dari Notion internal integration (diawali `ntn_`) |

### Variables (Repository variables)

| Nama | Isi |
|---|---|
| `NOTION_DATA_SOURCE_ID` | ID data source database "Threads Content Queue" di Notion |

## Cara pakai

1. Isi baris baru di database Notion, status **Draft** dulu buat direview.
2. Kalau udah oke, ubah status jadi **Terjadwal** (boleh isi "Tanggal Jadwal"
   kalau mau posting di waktu tertentu, kosongin kalau mau langsung posting
   di run berikutnya).
3. Workflow jalan otomatis tiap 30 menit (lihat `.github/workflows/publish.yml`).
   Bisa juga di-trigger manual: tab **Actions** → **Publish scheduled Threads
   posts** → **Run workflow**.
4. Setelah posting, status baris otomatis jadi **Sudah Posting** dan kolom
   **Post ID** keisi. Kalau gagal, status jadi **Gagal** — cek log run-nya
   di tab Actions.

## Catatan

- Access token Threads expired tiap ~60 hari, perlu di-generate ulang dari
  Meta Developer dashboard dan diupdate di secret `THREADS_ACCESS_TOKEN`.
- Reply di Threads gak kehitung ke limit 250 post/hari, cuma post utama
  (root) yang kehitung.
