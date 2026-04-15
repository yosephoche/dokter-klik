*DokterKlik — Product Requirements Document*

**PRODUCT REQUIREMENTS DOCUMENT**

**DokterKlik**

Platform SaaS Manajemen Klinik Cerdas

*Solusi Digital Terintegrasi SATUSEHAT untuk Klinik Pratama*

| **Versi** | 1.0 |
| --- | --- |
| **Tanggal** | 15 April 2026 |
| **Status** | Draft |
| **Klasifikasi** | Rahasia / Internal |

**Daftar Isi**

# **1. Ringkasan Eksekutif**

DokterKlik adalah platform Software-as-a-Service (SaaS) manajemen klinik yang dirancang khusus untuk klinik pratama dan dokter praktik mandiri di Indonesia. Platform ini menggabungkan Electronic Medical Record (EMR) berbasis SOAP, integrasi wajib SATUSEHAT Kemenkes, sistem antrean real-time, serta fitur kecerdasan buatan untuk pencatatan medis otomatis.

Visi utama DokterKlik adalah memangkas waktu administratif dokter hingga 60% sehingga mereka dapat memberikan fokus penuh kepada pasien, sekaligus meningkatkan retensi pasien melalui pengalaman digital yang modern dan nyaman.

## **1.1 Problem Statement**

Mayoritas klinik pratama dan dokter praktik mandiri di Indonesia masih mengandalkan pencatatan manual (buku register, kertas resep, Excel). Situasi ini menimbulkan beberapa permasalahan kritis:

- Ketidakpatuhan regulasi: PMK No. 24/2022 mewajibkan integrasi data rekam medis elektronik ke platform SATUSEHAT, namun sebagian besar klinik kecil belum memiliki sistem yang mampu melakukannya.

- Inefisiensi operasional: Dokter menghabiskan 30-40% waktu kerja untuk tugas administratif seperti menulis resep, menghitung tagihan, dan mencatat rekam medis.

- Pengalaman pasien buruk: Antrean panjang tanpa estimasi waktu, resep yang harus ditulis ulang, dan tidak adanya akses riwayat kesehatan mandiri.

- Kehilangan data: Catatan kertas rentan rusak, hilang, atau sulit dilacak untuk keperluan audit dan kontinuitas perawatan.

## **1.2 Solusi yang Ditawarkan**

DokterKlik menjawab permasalahan tersebut dengan menyediakan satu platform terintegrasi yang mencakup pencatatan medis digital, manajemen operasional klinik, dan kanal komunikasi pasien, semuanya dengan harga terjangkau (Rp 150.000 – Rp 300.000/bulan) dan antarmuka yang sederhana agar mudah diadopsi bahkan oleh dokter yang tidak terbiasa dengan teknologi.

## **1.3 Target Pengguna**

| **Persona** | **Deskripsi** | **Kebutuhan Utama** |
| --- | --- | --- |
| **Dokter Umum / Spesialis** | Dokter praktik mandiri atau dokter klinik kecil, usia 30–60 tahun | EMR cepat, auto-coding ICD, integrasi SATUSEHAT, resep digital |
| **Staf Administrasi** | Petugas pendaftaran, kasir, dan farmasi klinik | Billing otomatis, manajemen antrean, inventori apotek |
| **Pasien** | Pasien klinik dari berbagai usia dan tingkat literasi digital | Booking via WhatsApp, antrean real-time, riwayat kesehatan mandiri |
| **Pemilik / Manajemen Klinik** | Pemilik klinik yang memantau performa bisnis | Dashboard performa, laporan keuangan, analitik pasien |

# **2. Fitur Operasional ****&**** Dokter (The “Workhorse”)**

Tujuan utama kategori fitur ini adalah memangkas waktu administratif agar dokter bisa fokus sepenuhnya kepada pasien. Setiap fitur dirancang untuk meminimalkan jumlah klik dan input manual.

## **2.1 Smart EMR dengan SOAP**

### **2.1.1 Deskripsi**

Sistem pencatatan rekam medis elektronik berbasis metodologi SOAP (Subjective, Objective, Assessment, Plan) yang menjadi standar dokumentasi klinis. Sistem ini menyediakan template yang dapat dikustomisasi sesuai spesialisasi dokter.

### **2.1.2 Kebutuhan Fungsional**

| **ID** | **Requirement** | **Prioritas** |
| --- | --- | --- |
| **FR-EMR-01** | Form SOAP dengan 4 tab terpisah: Subjective, Objective, Assessment, Plan | Must Have |
| **FR-EMR-02** | Template bawaan untuk minimal 5 spesialisasi: Umum, Anak, Kulit & Kelamin, THT, Mata | Must Have |
| **FR-EMR-03** | Kemampuan membuat dan menyimpan template kustom per dokter | Should Have |
| **FR-EMR-04** | Auto-save setiap 30 detik untuk mencegah kehilangan data saat pengisian | Must Have |
| **FR-EMR-05** | Riwayat kunjungan pasien sebelumnya dapat diakses langsung dari form SOAP aktif | Must Have |
| **FR-EMR-06** | Pencarian cepat pasien berdasarkan nama, NIK, atau nomor rekam medis | Must Have |
| **FR-EMR-07** | Kemampuan melampirkan file penunjang (foto luka, hasil lab, USG) ke rekam medis | Should Have |

## **2.2 Integrasi SATUSEHAT (Wajib)**

### **2.2.1 Deskripsi**

Fitur sinkronisasi otomatis data rekam medis ke platform SATUSEHAT Kemenkes sesuai amanat PMK No. 24 Tahun 2022. Ini merupakan selling point utama DokterKlik karena kepatuhan regulasi menjadi kebutuhan mendesak bagi seluruh fasilitas kesehatan di Indonesia.

### **2.2.2 Standar Teknis**

- **HL7 FHIR R4: **Standar data kesehatan internasional yang digunakan SATUSEHAT. Seluruh resource (Patient, Encounter, Condition, Observation, MedicationRequest) harus divalidasi menggunakan library fhir.resources di Python.

- **OAuth 2.0 Client Credentials: **Autentikasi ke API SATUSEHAT menggunakan client_id dan client_secret yang diperoleh dari portal SATUSEHAT.

- **Retry Mechanism: **Implementasi exponential backoff untuk penanganan kegagalan sinkronisasi (maksimal 5 retry).

### **2.2.3 Kebutuhan Fungsional**

| **ID** | **Requirement** | **Prioritas** |
| --- | --- | --- |
| **FR-SS-01** | Sinkronisasi otomatis data pasien baru ke SATUSEHAT sebagai resource Patient | Must Have |
| **FR-SS-02** | Sinkronisasi data kunjungan (Encounter) setelah rekam medis SOAP selesai diisi | Must Have |
| **FR-SS-03** | Pengiriman data diagnosis (Condition) dengan kode ICD-10 yang tervalidasi | Must Have |
| **FR-SS-04** | Dashboard monitoring status sinkronisasi per pasien (sukses/gagal/pending) | Must Have |
| **FR-SS-05** | Logging lengkap setiap request/response ke API SATUSEHAT untuk audit trail | Must Have |
| **FR-SS-06** | Notifikasi ke admin klinik jika terjadi kegagalan sinkronisasi berulang | Should Have |
| **FR-SS-07** | Fitur re-sync manual untuk data yang gagal sinkronisasi | Must Have |

## **2.3 Auto-Coding ICD-10 ****&**** ICD-9**

### **2.3.1 Deskripsi**

Fitur pencarian dan pemilihan kode diagnosis (ICD-10) dan kode tindakan (ICD-9-CM) secara otomatis. Dokter cukup mengetikkan nama penyakit atau gejala dalam bahasa Indonesia maupun Inggris, dan sistem akan menampilkan saran kode yang relevan.

### **2.3.2 Kebutuhan Fungsional**

| **ID** | **Requirement** | **Prioritas** |
| --- | --- | --- |
| **FR-ICD-01** | Autocomplete ICD-10 dengan pencarian berdasarkan nama penyakit (ID/EN) dan kode | Must Have |
| **FR-ICD-02** | Autocomplete ICD-9-CM untuk kode tindakan medis | Should Have |
| **FR-ICD-03** | Menampilkan deskripsi lengkap kode beserta hierarki (chapter, block, category) | Should Have |
| **FR-ICD-04** | Menyimpan riwayat kode yang sering digunakan per dokter untuk akses cepat | Should Have |
| **FR-ICD-05** | Validasi kode ICD sebelum sinkronisasi ke SATUSEHAT | Must Have |

## **2.4 Manajemen Inventori ****&**** Apotek Mini**

### **2.4.1 Deskripsi**

Sistem pengelolaan stok obat dan alat kesehatan (alkes) dengan fitur pengingat otomatis saat stok menipis. Dirancang untuk apotek internal klinik dengan skala kecil hingga menengah.

### **2.4.2 Kebutuhan Fungsional**

| **ID** | **Requirement** | **Prioritas** |
| --- | --- | --- |
| **FR-INV-01** | Database obat dan alkes dengan informasi nama, satuan, harga beli, harga jual, dan stok | Must Have |
| **FR-INV-02** | Pencatatan otomatis pengurangan stok saat obat diresepkan dalam EMR | Must Have |
| **FR-INV-03** | Notifikasi otomatis (in-app dan WhatsApp) saat stok mencapai batas minimum yang dikonfigurasi | Must Have |
| **FR-INV-04** | Pencatatan tanggal kadaluarsa obat dengan peringatan 3 bulan sebelumnya | Should Have |
| **FR-INV-05** | Laporan stock opname bulanan dan riwayat pergerakan stok | Should Have |
| **FR-INV-06** | Fitur pencatatan penerimaan barang dari supplier (purchase order sederhana) | Could Have |

## **2.5 Billing ****&**** Invoicing Terintegrasi**

### **2.5.1 Deskripsi**

Sistem penghitungan biaya otomatis yang terintegrasi langsung dengan EMR dan inventori apotek. Mendukung berbagai metode pembayaran digital untuk kenyamanan pasien.

### **2.5.2 Kebutuhan Fungsional**

| **ID** | **Requirement** | **Prioritas** |
| --- | --- | --- |
| **FR-BIL-01** | Perhitungan otomatis total biaya: konsultasi + tindakan + obat berdasarkan data EMR | Must Have |
| **FR-BIL-02** | Pencetakan/pengiriman invoice digital ke pasien (PDF atau WhatsApp) | Must Have |
| **FR-BIL-03** | Integrasi pembayaran QRIS (melalui payment gateway seperti Midtrans/Xendit) | Must Have |
| **FR-BIL-04** | Integrasi pembayaran Virtual Account (VA) bank-bank utama | Should Have |
| **FR-BIL-05** | Pencatatan pembayaran tunai dengan fungsi kembalian otomatis | Must Have |
| **FR-BIL-06** | Riwayat transaksi lengkap dengan filter tanggal, metode bayar, dan status | Must Have |

## **2.6 Dashboard Performa Klinik**

### **2.6.1 Deskripsi**

Dashboard analitik yang menyajikan laporan harian dan bulanan mengenai performa klinik secara real-time, menghilangkan kebutuhan perhitungan manual di spreadsheet.

### **2.6.2 Kebutuhan Fungsional**

| **ID** | **Requirement** | **Prioritas** |
| --- | --- | --- |
| **FR-DSH-01** | Ringkasan harian: jumlah pasien, omzet, dan rata-rata waktu tunggu | Must Have |
| **FR-DSH-02** | Laporan bulanan: tren jumlah pasien, pendapatan, dan 10 diagnosis terbanyak | Must Have |
| **FR-DSH-03** | Daftar obat paling laku (top 20) dengan tren pergerakan stok | Should Have |
| **FR-DSH-04** | Grafik perbandingan performa antar-periode (bulan ke bulan, tahun ke tahun) | Should Have |
| **FR-DSH-05** | Export laporan ke format PDF dan CSV | Should Have |
| **FR-DSH-06** | Role-based access: dokter hanya melihat data pasiennya, admin melihat seluruh klinik | Must Have |

# **3. Fitur Pengalaman Pasien (The “Retention”)**

Kategori fitur ini bertujuan membuat pasien merasa nyaman, dihargai, dan tidak merasa membuang waktu saat berkunjung ke klinik. Retensi pasien adalah kunci pertumbuhan klinik.

## **3.1 Sistem Antrean Real-Time (Live Queue)**

Pasien dapat melihat nomor antrean yang sedang dilayani melalui WhatsApp atau portal web, sehingga mereka dapat mengatur waktu kedatangan dan tidak perlu menunggu lama di ruang tunggu.

| **ID** | **Requirement** | **Prioritas** |
| --- | --- | --- |
| **FR-QUE-01** | Tampilan antrean real-time di portal web yang dapat diakses pasien tanpa login | Must Have |
| **FR-QUE-02** | Notifikasi WhatsApp otomatis saat giliran pasien tinggal 3 nomor lagi | Must Have |
| **FR-QUE-03** | Estimasi waktu tunggu berdasarkan rata-rata durasi konsultasi dokter | Should Have |
| **FR-QUE-04** | Fitur panggilan antrean dari dashboard staf administrasi | Must Have |
| **FR-QUE-05** | Display antrean untuk layar TV di ruang tunggu klinik (mode fullscreen) | Could Have |

## **3.2 Booking Online via WhatsApp**

Integrasi dengan WhatsApp Business API agar pasien dapat mendaftar kunjungan hanya dengan mengirim pesan seperti “Daftar”. Sistem chatbot akan memandu proses pendaftaran secara otomatis.

| **ID** | **Requirement** | **Prioritas** |
| --- | --- | --- |
| **FR-WA-01** | Chatbot WhatsApp untuk pendaftaran kunjungan dengan alur percakapan terstruktur | Must Have |
| **FR-WA-02** | Konfirmasi booking otomatis berisi tanggal, jam, dan nomor antrean | Must Have |
| **FR-WA-03** | Kemampuan memilih dokter dan jadwal praktik yang tersedia | Should Have |
| **FR-WA-04** | Pengingat H-1 dan H-hari via WhatsApp sebelum jadwal kunjungan | Must Have |
| **FR-WA-05** | Integrasi dengan WhatsApp Business API (Cloud API Meta) melalui provider resmi | Must Have |

## **3.3 E-Prescription (Resep Digital)**

Resep yang dibuat dokter dalam EMR langsung dikirim secara digital ke bagian farmasi internal klinik dan/atau ke ponsel pasien, menghilangkan kebutuhan resep kertas.

| **ID** | **Requirement** | **Prioritas** |
| --- | --- | --- |
| **FR-RX-01** | Pembuatan resep digital terintegrasi langsung dari form SOAP (bagian Plan) | Must Have |
| **FR-RX-02** | Pengiriman resep ke dashboard farmasi internal secara real-time | Must Have |
| **FR-RX-03** | Pengiriman salinan resep ke WhatsApp pasien dalam format yang mudah dibaca | Should Have |
| **FR-RX-04** | Peringatan interaksi obat dasar (drug-drug interaction) saat meresepkan | Could Have |
| **FR-RX-05** | Database obat terintegrasi dengan inventori sehingga dokter tahu ketersediaan stok | Must Have |

## **3.4 Pengingat Kontrol Otomatis**

Sistem mengirimkan pesan otomatis ke pasien untuk jadwal kontrol ulang, vaksinasi berikutnya, atau tindak lanjut lainnya yang telah dijadwalkan dokter.

| **ID** | **Requirement** | **Prioritas** |
| --- | --- | --- |
| **FR-REM-01** | Dokter dapat menjadwalkan pengingat kontrol dari form SOAP | Must Have |
| **FR-REM-02** | Pengiriman pengingat otomatis via WhatsApp pada H-3 dan H-hari | Must Have |
| **FR-REM-03** | Template pesan pengingat yang dapat dikustomisasi per klinik | Should Have |
| **FR-REM-04** | Dashboard daftar pasien yang perlu kontrol ulang minggu ini | Should Have |

## **3.5 Portal Riwayat Kesehatan Mandiri**

Portal web yang memungkinkan pasien mengakses riwayat kunjungan, hasil laboratorium, dan catatan medis mereka sendiri secara aman. Konsep ini mirip dengan buku KIA digital namun berlaku untuk semua kelompok usia.

| **ID** | **Requirement** | **Prioritas** |
| --- | --- | --- |
| **FR-PTL-01** | Halaman login pasien dengan autentikasi OTP via WhatsApp | Must Have |
| **FR-PTL-02** | Tampilan kronologis seluruh riwayat kunjungan dengan ringkasan diagnosis | Must Have |
| **FR-PTL-03** | Akses unduh hasil laboratorium dan dokumen penunjang dalam format PDF | Should Have |
| **FR-PTL-04** | Tampilan riwayat resep obat yang pernah diterima | Should Have |
| **FR-PTL-05** | Desain responsif yang optimal untuk perangkat mobile (mobile-first) | Must Have |

# **4. Fitur Masa Depan (The “Edge”)**

Fitur-fitur berikut dirancang sebagai diferensiasi kompetitif DokterKlik dari platform manajemen klinik yang sudah ada. Pengembangan dilakukan pada fase lanjutan setelah fitur inti stabil.

## **4.1 AI Medical Scribbler (Voice-to-Text)**

Fitur kecerdasan buatan yang mengkonversi ucapan dokter saat konsultasi menjadi catatan medis terstruktur dalam format SOAP secara otomatis. Fitur ini menghilangkan hambatan “malas mengetik” yang sering dialami dokter senior.

### **4.1.1 Kebutuhan Fungsional**

| **ID** | **Requirement** | **Prioritas** |
| --- | --- | --- |
| **FR-AI-01** | Speech-to-text real-time dengan dukungan Bahasa Indonesia dan istilah medis | Must Have (Phase 3) |
| **FR-AI-02** | Konversi otomatis transkrip ke format SOAP dengan klasifikasi per bagian | Must Have (Phase 3) |
| **FR-AI-03** | Review dan edit oleh dokter sebelum catatan disimpan ke EMR | Must Have (Phase 3) |
| **FR-AI-04** | Saran kode ICD-10 berdasarkan hasil transkrip AI | Should Have (Phase 3) |
| **FR-AI-05** | Mode offline recording dengan sinkronisasi setelah koneksi kembali | Could Have (Phase 3) |

## **4.2 Telekonsultasi Hybrid**

Fitur konsultasi video untuk pasien yang hanya perlu menanyakan hasil laboratorium, follow-up ringan, atau konsultasi lanjutan tanpa perlu datang langsung ke klinik.

### **4.2.1 Kebutuhan Fungsional**

| **ID** | **Requirement** | **Prioritas** |
| --- | --- | --- |
| **FR-TEL-01** | Video call terintegrasi dalam platform (WebRTC-based) tanpa aplikasi tambahan | Must Have (Phase 3) |
| **FR-TEL-02** | Penjadwalan slot telekonsultasi yang terpisah dari jadwal kunjungan fisik | Must Have (Phase 3) |
| **FR-TEL-03** | Kemampuan berbagi layar dan dokumen selama sesi telekonsultasi | Should Have (Phase 3) |
| **FR-TEL-04** | Pencatatan EMR terintegrasi selama/setelah sesi telekonsultasi | Must Have (Phase 3) |
| **FR-TEL-05** | Pembayaran online terintegrasi sebelum sesi dimulai | Must Have (Phase 3) |

# **5. Arsitektur Teknis**

Arsitektur DokterKlik dirancang dengan prinsip kesederhanaan, keamanan, dan skalabilitas bertahap. Pemilihan teknologi mempertimbangkan ketersediaan developer di Indonesia serta kematangan ekosistem.

## **5.1 Technology Stack**

| **Komponen** | **Teknologi** | **Justifikasi** |
| --- | --- | --- |
| **Backend Framework** | Django (LTS terbaru) | Ekosistem matang, ORM kuat, django-rest-framework untuk API, komunitas besar di Indonesia |
| **Database** | PostgreSQL | Reliabilitas tinggi untuk data medis terstruktur, dukungan JSONB untuk data fleksibel, enkripsi level kolom |
| **Task Queue** | Celery + Redis | Menangani proses background: sinkronisasi SATUSEHAT, pengiriman WhatsApp massal, generate laporan |
| **Frontend** | HTMX + Jinja2 | Kompleksitas rendah, server-rendered, reload parsial tanpa SPA framework, cepat dipelajari tim kecil |
| **Cache Layer** | Redis | Session management, cache query dashboard, rate limiting API |
| **File Storage** | MinIO / S3-compatible | Penyimpanan file medis (foto, hasil lab) dengan enkripsi at-rest |
| **Reverse Proxy** | Nginx | SSL termination, static file serving, load balancing |
| **Containerization** | Docker + Docker Compose | Konsistensi environment dev/staging/production, easy deployment |

## **5.2 Keamanan Data**

Keamanan data medis adalah prioritas absolut. DokterKlik mengimplementasikan lapisan keamanan berlapis sesuai standar industri kesehatan.

### **5.2.1 Enkripsi**

- **At Rest: **Seluruh data sensitif (rekam medis, data pribadi pasien) dienkripsi menggunakan library cryptography (Fernet symmetric encryption) sebelum disimpan ke database. PostgreSQL Transparent Data Encryption (TDE) diaktifkan sebagai lapisan tambahan.

- **In Transit: **Wajib HTTPS/TLS 1.3 untuk seluruh komunikasi. SSL certificate dikelola melalui Let’s Encrypt dengan auto-renewal.

- **Key Management: **Encryption key disimpan terpisah dari database menggunakan environment variables (.env) yang tidak masuk ke version control.

### **5.2.2 Akses ****&**** Autentikasi**

- Role-Based Access Control (RBAC): Dokter, Staf Admin, Farmasi, Pemilik Klinik, Pasien masing-masing memiliki hak akses berbeda.

- Multi-Factor Authentication (MFA) opsional untuk akun dokter dan admin.

- Session timeout otomatis setelah 30 menit tidak aktif.

- Audit log seluruh akses data medis pasien.

### **5.2.3 Compliance**

- Kepatuhan terhadap UU PDP (Perlindungan Data Pribadi) No. 27 Tahun 2022.

- Kepatuhan terhadap PMK No. 24 Tahun 2022 tentang Rekam Medis Elektronik.

- Data hosting wajib di data center yang berlokasi di Indonesia.

## **5.3 Integrasi SATUSEHAT – Detail Teknis**

### **5.3.1 Alur Sinkronisasi**

- Dokter menyelesaikan pengisian SOAP dan menekan tombol “Simpan”.

- Sistem memvalidasi kelengkapan data dan kode ICD menggunakan fhir.resources.

- Celery task dijalankan secara asinkron untuk mengirim data ke API SATUSEHAT.

- Resource FHIR yang dikirim: Patient, Encounter, Condition, Observation, MedicationRequest.

- Response dari SATUSEHAT dicatat di tabel sync_log dengan status: success, failed, atau pending.

- Jika gagal, sistem melakukan retry dengan exponential backoff (maks 5x, interval 1-16 menit).

- Dashboard monitoring menampilkan status real-time seluruh sinkronisasi.

### **5.3.2 Logging ****&**** Monitoring**

- Setiap request/response ke API SATUSEHAT di-log secara lengkap (timestamp, payload, HTTP status, response body).

- Alert otomatis ke admin klinik jika failure rate melebihi 10% dalam 1 jam.

- Retensi log minimal 5 tahun sesuai regulasi rekam medis.

# **6. Non-Functional Requirements**

| **Kategori** | **Requirement** | **Target** |
| --- | --- | --- |
| **Performa** | Waktu muat halaman utama dashboard | < 2 detik |
| **Performa** | Waktu pencarian pasien dan autocomplete ICD | < 500ms |
| **Performa** | Waktu sinkronisasi SATUSEHAT per encounter | < 10 detik |
| **Ketersediaan** | Uptime sistem keseluruhan | 99.5% |
| **Ketersediaan** | RTO (Recovery Time Objective) | < 4 jam |
| **Ketersediaan** | RPO (Recovery Point Objective) | < 1 jam |
| **Skalabilitas** | Mendukung minimal jumlah klinik secara bersamaan | 500 klinik |
| **Skalabilitas** | Mendukung minimal jumlah rekam medis per klinik | 100.000 records |
| **Usability** | Waktu onboarding pengguna baru tanpa training formal | < 1 jam |
| **Usability** | Mendukung browser Chrome, Firefox, Safari, Edge versi terbaru | 100% |
| **Usability** | Responsif untuk resolusi layar ≥ 360px (mobile-first) | 100% |
| **Keamanan** | Seluruh data medis terenkripsi at-rest dan in-transit | 100% |
| **Keamanan** | Audit log akses data pasien | 100% |

# **7. Rencana Bisnis ****&**** Monetisasi**

## **7.1 Model Bisnis**

DokterKlik mengadopsi model berlangganan bulanan (SaaS subscription) dengan harga yang dirancang kompetitif dan terjangkau bagi klinik di seluruh Indonesia, termasuk daerah.

## **7.2 Tabel Harga ****&**** Paket**

| **Fitur** | **Starter (Gratis)** | **Profesional (Rp 150rb/bln)** | **Klinik Plus (Rp 300rb/bln)** |
| --- | --- | --- | --- |
| **Pasien per bulan** | 20 pasien | Unlimited | Unlimited |
| **Smart EMR (SOAP)** | ✓ | ✓ | ✓ |
| **Integrasi SATUSEHAT** | ✓ | ✓ | ✓ |
| **Auto-Coding ICD** | ✓ | ✓ | ✓ |
| **Billing ****&**** Invoicing** | Dasar (tunai) | QRIS + VA | QRIS + VA + Laporan |
| **Antrean Real-Time** | ✓ | ✓ | ✓ |
| **Booking WhatsApp** | ✗ | ✓ | ✓ |
| **E-Prescription** | ✗ | ✓ | ✓ |
| **Pengingat Kontrol** | ✗ | ✓ | ✓ |
| **Inventori Apotek** | ✗ | Dasar | Lengkap + Kadaluarsa |
| **Dashboard Analytics** | ✗ | Dasar | Lengkap + Export |
| **Portal Pasien** | ✗ | ✗ | ✓ |
| **Multi-Dokter** | 1 dokter | 1 dokter | Hingga 5 dokter |
| **Support** | Komunitas | WhatsApp (jam kerja) | WhatsApp + Prioritas |

## **7.3 Strategi Freemium**

Paket Starter gratis untuk 20 pasien per bulan bertujuan memberikan kesempatan kepada dokter untuk merasakan kemudahan dan nilai platform sebelum berkomitmen untuk berlangganan. Strategi ini efektif karena:

- Mengurangi barrier to entry untuk dokter yang skeptis terhadap teknologi.

- Memberikan waktu bagi dokter untuk merasakan efisiensi dan integrasi SATUSEHAT.

- Natural upsell: begitu pasien melebihi 20/bulan, dokter sudah bergantung pada sistem.

## **7.4 Unique Selling Proposition (USP)**

- **SATUSEHAT-First: **Satu-satunya platform di kelas harga ini yang menjadikan integrasi SATUSEHAT sebagai fitur inti, bukan add-on.

- **Kecepatan ****&**** Kesederhanaan: **UI berbasis HTMX tanpa SPA bloat, memastikan akses cepat bahkan di koneksi internet klinik daerah.

- **WhatsApp-Native: **Seluruh interaksi pasien melalui WhatsApp, platform yang sudah familiar bagi 90%+ masyarakat Indonesia.

- **Migrasi Mudah: **Tim onboarding membantu input data pasien lama dari buku register ke sistem digital, meminimalkan hambatan adopsi.

# **8. Roadmap Pengembangan**

| **Fase** | **Timeline** | **Deliverable Utama** | **Milestone** |
| --- | --- | --- | --- |
| **Phase 1** | Bulan 1–4 | Smart EMR (SOAP), Integrasi SATUSEHAT, Auto-Coding ICD, Billing dasar, Antrean real-time | **MVP Launch** |
| **Phase 2** | Bulan 5–8 | Booking WhatsApp, E-Prescription, Inventori Apotek, Pengingat Kontrol, Dashboard Analytics | **Feature Complete** |
| **Phase 3** | Bulan 9–12 | Portal Pasien, AI Medical Scribbler (Beta), Telekonsultasi Hybrid | **Edge Features** |
| **Phase 4** | Bulan 13+ | Optimasi performa, skalabilitas multi-klinik, integrasi BPJS, mobile app native | **Scale ****&**** Expand** |

# **9. Metrik Keberhasilan (KPI)**

Berikut adalah indikator kunci yang digunakan untuk mengukur keberhasilan DokterKlik pada 12 bulan pertama setelah peluncuran:

| **Metrik** | **Target 6 Bulan** | **Target 12 Bulan** |
| --- | --- | --- |
| **Jumlah klinik terdaftar (aktif)** | 50 klinik | 200 klinik |
| **Conversion rate Starter → Berbayar** | 15% | 25% |
| **Tingkat keberhasilan sinkronisasi SATUSEHAT** | > 95% | > 99% |
| **Monthly Recurring Revenue (MRR)** | Rp 15 juta | Rp 50 juta |
| **Churn rate bulanan** | < 8% | < 5% |
| **Net Promoter Score (NPS)** | > 40 | > 50 |
| **Rata-rata waktu pengisian SOAP per kunjungan** | < 5 menit | < 3 menit |

# **10. Risiko ****&**** Mitigasi**

| **Risiko** | **Dampak** | **Strategi Mitigasi** |
| --- | --- | --- |
| **Perubahan API SATUSEHAT** | **Tinggi** | Abstraction layer untuk isolasi perubahan API, monitoring changelog SATUSEHAT, versioning adapter pattern |
| **Resistensi adopsi dokter senior** | **Tinggi** | UI ultra-sederhana, fitur AI Scribbler untuk voice input, program onboarding 1-on-1, trial gratis |
| **Ketidakstabilan koneksi internet daerah** | **Sedang** | Offline-first approach untuk EMR, sync saat koneksi tersedia, optimasi payload HTMX |
| **Kebocoran data medis** | **Kritis** | Enkripsi berlapis (at-rest + in-transit), audit log, penetration testing berkala, compliance UU PDP |
| **Persaingan dengan platform mapan** | **Sedang** | Fokus pada harga terjangkau, SATUSEHAT-first, dan target niche klinik pratama/dokter mandiri |
| **Ketergantungan pada WhatsApp API** | **Sedang** | Fallback ke SMS gateway, arsitektur messaging abstrak yang bisa swap provider |

# **11. Lampiran**

## **11.1 Glosarium**

| **Istilah** | **Definisi** |
| --- | --- |
| **SOAP** | Subjective, Objective, Assessment, Plan — metodologi standar pencatatan medis |
| **SATUSEHAT** | Platform data kesehatan nasional Kemenkes RI untuk integrasi fasilitas kesehatan |
| **HL7 FHIR** | Health Level Seven Fast Healthcare Interoperability Resources — standar pertukaran data kesehatan |
| **ICD-10** | International Classification of Diseases, 10th Revision — sistem klasifikasi diagnosis penyakit WHO |
| **ICD-9-CM** | International Classification of Diseases, 9th Revision, Clinical Modification — klasifikasi tindakan medis |
| **EMR** | Electronic Medical Record — rekam medis elektronik |
| **QRIS** | Quick Response Code Indonesian Standard — standar pembayaran QR code nasional |
| **PMK** | Peraturan Menteri Kesehatan |
| **UU PDP** | Undang-Undang Perlindungan Data Pribadi No. 27 Tahun 2022 |
| **Klinik Pratama** | Fasilitas kesehatan tingkat pertama yang menyelenggarakan pelayanan kesehatan dasar |

## **11.2 Referensi Regulasi**

- PMK No. 24 Tahun 2022 tentang Rekam Medis

- UU No. 27 Tahun 2022 tentang Perlindungan Data Pribadi

- Pedoman Teknis Integrasi SATUSEHAT — Kementerian Kesehatan RI

- HL7 FHIR R4 Specification — https://hl7.org/fhir/R4/

*--- Akhir Dokumen ---*