
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from scipy.stats import spearmanr
from pathlib import Path

DB = Path("pelita.db")

st.set_page_config(
    page_title="PELITA - Learning Gap",
    page_icon="📘",
    layout="wide"
)

# ---------- DATABASE ----------
def connect():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS akademik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kode TEXT NOT NULL,
                jenjang TEXT NOT NULL,
                kelas TEXT,
                mapel TEXT NOT NULL,
                periode TEXT NOT NULL,
                kehadiran REAL NOT NULL,
                tugas REAL NOT NULL,
                nilai REAL NOT NULL,
                kompetensi TEXT NOT NULL,
                target REAL NOT NULL
            )
        """)

def get_data():
    with connect() as conn:
        return pd.read_sql_query(
            "SELECT * FROM akademik ORDER BY kode, periode",
            conn
        )

def save_record(values):
    with connect() as conn:
        conn.execute("""
            INSERT INTO akademik
            (kode, jenjang, kelas, mapel, periode,
             kehadiran, tugas, nilai, kompetensi, target)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, values)

def update_record(record_id, values):
    with connect() as conn:
        conn.execute("""
            UPDATE akademik
            SET kode=?, jenjang=?, kelas=?, mapel=?, periode=?,
                kehadiran=?, tugas=?, nilai=?, kompetensi=?, target=?
            WHERE id=?
        """, (*values, record_id))

def delete_record(record_id):
    with connect() as conn:
        conn.execute(
            "DELETE FROM akademik WHERE id=?",
            (record_id,)
        )

init_db()

# ---------- HELPER ----------
def make_alert(row):
    reasons = []

    if row["kehadiran"] < 75:
        reasons.append("Kehadiran di bawah 75%")

    if row["nilai"] < row["target"]:
        reasons.append("Nilai belum mencapai target")

    if row["tugas"] < 70:
        reasons.append("Penyelesaian tugas perlu diperhatikan")

    if len(reasons) >= 2:
        status = "Perlu evaluasi lebih lanjut"
    elif len(reasons) == 1:
        status = "Perlu pendampingan"
    else:
        status = "Perlu pemantauan berkala"

    return status, "; ".join(reasons)

def add_demo_data():
    demo = [
        ("P001", "SD", "5", "Matematika", "P1", 95, 90, 82, "Operasi hitung", 75),
        ("P001", "SD", "5", "Matematika", "P2", 90, 85, 78, "Operasi hitung", 75),
        ("P001", "SD", "5", "Matematika", "P3", 85, 80, 70, "Operasi hitung", 75),
        ("P002", "SMP", "8", "IPA", "P1", 90, 90, 80, "Sistem pencernaan", 75),
        ("P002", "SMP", "8", "IPA", "P2", 92, 85, 84, "Sistem pencernaan", 75),
        ("P002", "SMP", "8", "IPA", "P3", 95, 90, 88, "Sistem pencernaan", 75),
        ("P003", "SMA", "11", "Fisika", "P1", 80, 75, 68, "Gerak lurus", 75),
        ("P003", "SMA", "11", "Fisika", "P2", 78, 70, 65, "Gerak lurus", 75),
        ("P003", "SMA", "11", "Fisika", "P3", 75, 65, 60, "Gerak lurus", 75),
        ("P004", "Perguruan Tinggi", "1", "Statistika", "P1", 95, 95, 90, "Statistik dasar", 75),
        ("P004", "Perguruan Tinggi", "1", "Statistika", "P2", 95, 90, 88, "Statistik dasar", 75),
    ]
    for row in demo:
        save_record(row)

# ---------- SIDEBAR ----------
st.sidebar.title("📘 PELITA")
st.sidebar.caption("Pemetaan dan Evaluasi Learning Gap")
page = st.sidebar.radio(
    "Navigasi",
    [
        "Dashboard",
        "Input Data",
        "Kelola Data",
        "Analisis",
        "Peringatan Dini"
    ]
)

df = get_data()

st.title("PELITA")
st.caption(
    "Sistem Pemetaan dan Evaluasi Learning Gap Terintegrasi Akademik"
)

# ---------- DASHBOARD ----------
if page == "Dashboard":
    st.subheader("Dashboard Perkembangan Belajar")

    if df.empty:
        st.info("Belum ada data. Tambahkan data atau masukkan data simulasi.")
        if st.button("Masukkan Data Simulasi"):
            add_demo_data()
            st.success("Data simulasi berhasil ditambahkan.")
            st.rerun()
    else:
        total = df["kode"].nunique()
        avg = df["nilai"].mean()
        attendance = df["kehadiran"].mean()
        task_avg = df["tugas"].mean()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Kode Peserta", total)
        c2.metric("Rata-rata Nilai", f"{avg:.1f}")
        c3.metric("Rata-rata Kehadiran", f"{attendance:.1f}%")
        c4.metric("Penyelesaian Tugas", f"{task_avg:.1f}%")

        st.divider()
        left, right = st.columns(2)

        with left:
            by_level = (
                df.groupby("jenjang", as_index=False)["nilai"]
                .mean()
            )
            fig = px.bar(
                by_level,
                x="jenjang",
                y="nilai",
                title="Rata-rata Nilai per Jenjang",
                labels={"jenjang": "Jenjang", "nilai": "Rata-rata nilai"}
            )
            st.plotly_chart(fig, use_container_width=True)

        with right:
            trend = (
                df.groupby("periode", as_index=False)["nilai"]
                .mean()
            )
            fig = px.line(
                trend,
                x="periode",
                y="nilai",
                markers=True,
                title="Perkembangan Nilai per Periode",
                labels={"periode": "Periode", "nilai": "Rata-rata nilai"}
            )
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Data Akademik Terbaru")
        st.dataframe(df.tail(10), use_container_width=True)

# ---------- INPUT DATA ----------
elif page == "Input Data":
    st.subheader("Tambah Data Akademik")

    with st.form("form_input"):
        kode = st.text_input("Kode peserta", placeholder="Contoh: P005")
        jenjang = st.selectbox(
            "Jenjang",
            ["SD", "SMP", "SMA", "SMK", "Perguruan Tinggi"]
        )
        kelas = st.text_input("Kelas / semester")
        mapel = st.text_input("Mata pelajaran / mata kuliah")
        periode = st.text_input("Periode", placeholder="Contoh: P1")
        kehadiran = st.number_input(
            "Kehadiran (%)", 0.0, 100.0, 90.0
        )
        tugas = st.number_input(
            "Penyelesaian tugas (%)", 0.0, 100.0, 80.0
        )
        nilai = st.number_input(
            "Nilai akademik", 0.0, 100.0, 75.0
        )
        kompetensi = st.text_input(
            "Kompetensi yang dinilai",
            placeholder="Contoh: Operasi hitung"
        )
        target = st.number_input(
            "Target kompetensi", 0.0, 100.0, 75.0
        )

        submitted = st.form_submit_button("Simpan Data")

        if submitted:
            if not all([kode, mapel, periode, kompetensi]):
                st.error("Lengkapi seluruh kolom teks terlebih dahulu.")
            else:
                save_record((
                    kode, jenjang, kelas, mapel, periode,
                    kehadiran, tugas, nilai, kompetensi, target
                ))
                st.success("Data berhasil disimpan.")
                st.rerun()

# ---------- KELOLA DATA ----------
elif page == "Kelola Data":
    st.subheader("Kelola Data Akademik")

    if df.empty:
        st.info("Belum ada data untuk dikelola.")
    else:
        st.dataframe(df, use_container_width=True)

        st.markdown("### Ubah Data")
        selected_id = st.selectbox(
            "Pilih ID data",
            df["id"].tolist()
        )
        selected = df[df["id"] == selected_id].iloc[0]

        with st.form("form_edit"):
            kode = st.text_input("Kode peserta", str(selected["kode"]))
            jenjang = st.selectbox(
                "Jenjang",
                ["SD", "SMP", "SMA", "SMK", "Perguruan Tinggi"],
                index=["SD", "SMP", "SMA", "SMK", "Perguruan Tinggi"].index(
                    selected["jenjang"]
                )
            )
            kelas = st.text_input("Kelas / semester", str(selected["kelas"]))
            mapel = st.text_input("Mata pelajaran", str(selected["mapel"]))
            periode = st.text_input("Periode", str(selected["periode"]))
            kehadiran = st.number_input(
                "Kehadiran (%)", 0.0, 100.0,
                float(selected["kehadiran"])
            )
            tugas = st.number_input(
                "Penyelesaian tugas (%)", 0.0, 100.0,
                float(selected["tugas"])
            )
            nilai = st.number_input(
                "Nilai", 0.0, 100.0, float(selected["nilai"])
            )
            kompetensi = st.text_input(
                "Kompetensi", str(selected["kompetensi"])
            )
            target = st.number_input(
                "Target", 0.0, 100.0, float(selected["target"])
            )

            update = st.form_submit_button("Simpan Perubahan")

            if update:
                values = (
                    kode, jenjang, kelas, mapel, periode,
                    kehadiran, tugas, nilai, kompetensi, target
                )
                update_record(selected_id, values)
                st.success("Data berhasil diperbarui.")
                st.rerun()

        st.markdown("### Hapus Data")
        confirm = st.checkbox(
            f"Saya yakin ingin menghapus data ID {selected_id}"
        )
        if st.button("Hapus Data", disabled=not confirm):
            delete_record(selected_id)
            st.success("Data berhasil dihapus.")
            st.rerun()

    st.divider()
   
# ---------- ANALISIS LEARNING GAP ----------
elif page == "Analisis":
    st.subheader("Analisis Learning Gap")

    if df.empty:
        st.info("Belum ada data akademik untuk dianalisis.")

    else:
        st.write(
            "Analisis dilakukan dengan membandingkan "
            "nilai aktual peserta dengan target kompetensi."
        )

        # Filter data
        jenjang_pilihan = st.selectbox(
            "Pilih Jenjang",
            ["Semua"] + sorted(df["jenjang"].unique().tolist())
        )

        data_analisis = df.copy()

        if jenjang_pilihan != "Semua":
            data_analisis = data_analisis[
                data_analisis["jenjang"] == jenjang_pilihan
            ]

        mapel_pilihan = st.selectbox(
            "Pilih Mata Pelajaran",
            ["Semua"] + sorted(
                data_analisis["mapel"].unique().tolist()
            )
        )

        if mapel_pilihan != "Semua":
            data_analisis = data_analisis[
                data_analisis["mapel"] == mapel_pilihan
            ]

        # Menghitung learning gap
        data_analisis["gap"] = (
            data_analisis["target"] - data_analisis["nilai"]
        ).clip(lower=0)

        data_analisis["capaian"] = (
            data_analisis["nilai"] >= data_analisis["target"]
        )

        # Ringkasan analisis
        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Rata-rata Nilai",
            f"{data_analisis['nilai'].mean():.2f}"
        )

        col2.metric(
            "Rata-rata Learning Gap",
            f"{data_analisis['gap'].mean():.2f}"
        )

        col3.metric(
            "Kompetensi Tercapai",
            f"{data_analisis['capaian'].mean() * 100:.1f}%"
        )

        st.divider()

        # Pemetaan berdasarkan kompetensi
        st.markdown("### Pemetaan Kompetensi")

        pemetaan = (
            data_analisis.groupby("kompetensi", as_index=False)
            .agg(
                rata_nilai=("nilai", "mean"),
                target=("target", "mean"),
                rata_gap=("gap", "mean")
            )
        )

        st.dataframe(pemetaan, use_container_width=True)

        fig = px.bar(
            pemetaan,
            x="kompetensi",
            y=["rata_nilai", "target"],
            barmode="group",
            title="Perbandingan Nilai Aktual dan Target"
        )

        st.plotly_chart(fig, use_container_width=True)

        # Korelasi Spearman
        st.markdown("### Analisis Hubungan Kehadiran dan Nilai")

        if (
            len(data_analisis) >= 3
            and data_analisis["kehadiran"].nunique() > 1
            and data_analisis["nilai"].nunique() > 1
        ):
            korelasi, p_value = spearmanr(
                data_analisis["kehadiran"],
                data_analisis["nilai"]
            )

            st.metric(
                "Korelasi Spearman",
                f"{korelasi:.3f}"
            )

            st.caption(
                f"Nilai p-value: {p_value:.4f}. "
                "Korelasi menunjukkan hubungan, bukan sebab-akibat."
            )
        else:
            st.info(
                "Data belum cukup bervariasi untuk menghitung korelasi."
            )

# ---------- PERINGATAN DINI ----------
elif page == "Peringatan Dini":
    st.subheader("Sistem Peringatan Dini Akademik")

    st.write(
        "Sistem mengidentifikasi peserta yang membutuhkan "
        "pemantauan atau pendampingan berdasarkan data akademik."
    )

    if df.empty:
        st.info(
            "Belum ada data akademik. "
            "Silakan masukkan data terlebih dahulu."
        )

    else:
        # Membuat hasil peringatan untuk setiap catatan akademik
        hasil = df.copy()

        hasil["status"], hasil["indikator"] = zip(
            *hasil.apply(make_alert, axis=1)
        )

        # Rekomendasi berdasarkan status
        def rekomendasi(status):
            if status == "Perlu evaluasi lebih lanjut":
                return (
                    "Evaluasi pembelajaran dan susun "
                    "pendampingan individual."
                )
            elif status == "Perlu pendampingan":
                return (
                    "Lakukan pendampingan pada indikator "
                    "yang belum memenuhi target."
                )
            else:
                return (
                    "Pertahankan capaian dan lakukan "
                    "pemantauan berkala."
                )

        hasil["rekomendasi"] = hasil["status"].apply(
            rekomendasi
        )

        # Ringkasan status
        st.markdown("### Ringkasan Peringatan")

        evaluasi = (
            hasil["status"] == "Perlu evaluasi lebih lanjut"
        ).sum()

        pendampingan = (
            hasil["status"] == "Perlu pendampingan"
        ).sum()

        pemantauan = (
            hasil["status"] == "Perlu pemantauan berkala"
        ).sum()

        c1, c2, c3 = st.columns(3)

        c1.metric("Perlu Evaluasi", int(evaluasi))
        c2.metric("Perlu Pendampingan", int(pendampingan))
        c3.metric("Pemantauan Berkala", int(pemantauan))

        st.divider()

        # Tabel hasil identifikasi
        st.markdown("### Hasil Identifikasi Peserta")

        kolom = [
            "kode",
            "jenjang",
            "mapel",
            "periode",
            "kehadiran",
            "tugas",
            "nilai",
            "target",
            "indikator",
            "status",
            "rekomendasi"
        ]

        st.dataframe(
            hasil[kolom],
            use_container_width=True
        )

        # Filter status
        st.markdown("### Filter Peringatan")

        pilihan_status = st.selectbox(
            "Pilih status",
            [
                "Semua",
                "Perlu evaluasi lebih lanjut",
                "Perlu pendampingan",
                "Perlu pemantauan berkala"
            ]
        )

        if pilihan_status != "Semua":
            hasil_filter = hasil[
                hasil["status"] == pilihan_status
            ]
        else:
            hasil_filter = hasil

        st.dataframe(
            hasil_filter[kolom],
            use_container_width=True
        )

        # Unduh laporan
        csv = hasil.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Unduh Laporan Peringatan (CSV)",
            data=csv,
            file_name="laporan_peringatan_pelita.csv",
            mime="text/csv"
        )
